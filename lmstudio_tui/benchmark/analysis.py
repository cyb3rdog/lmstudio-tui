from __future__ import annotations

import statistics
from dataclasses import dataclass, field

from ..api.models import CompletionMetrics


@dataclass
class BenchmarkResult:
    model_id: str
    server_name: str
    runs: int
    # TPS
    mean_tps: float | None = None
    median_tps: float | None = None
    p95_tps: float | None = None
    p99_tps: float | None = None
    stdev_tps: float | None = None
    min_tps: float | None = None
    max_tps: float | None = None
    # TTFT
    mean_ttft_ms: float | None = None
    median_ttft_ms: float | None = None
    p95_ttft_ms: float | None = None
    p99_ttft_ms: float | None = None
    stdev_ttft_ms: float | None = None
    # Tokens
    avg_prompt_tokens: float = 0.0
    avg_completion_tokens: float = 0.0
    # Total latency
    mean_total_ms: float | None = None
    p95_total_ms: float | None = None
    # Raw
    raw_samples: list[CompletionMetrics] = field(default_factory=list)


def _percentile(data: list[float], p: float) -> float | None:
    if not data:
        return None
    s = sorted(data)
    idx = (p / 100) * (len(s) - 1)
    lo, hi = int(idx), min(int(idx) + 1, len(s) - 1)
    return s[lo] + (idx - lo) * (s[hi] - s[lo])


def _remove_iqr_outliers(data: list[float]) -> list[float]:
    if len(data) < 4:
        return data
    q1 = _percentile(data, 25) or 0.0
    q3 = _percentile(data, 75) or 0.0
    iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    return [x for x in data if lo <= x <= hi]


def analyze(
    samples: list[CompletionMetrics],
    model_id: str,
    server_name: str,
    remove_outliers: bool = True,
) -> BenchmarkResult:
    tps_raw = [s.tokens_per_second for s in samples if s.tokens_per_second is not None]
    ttft_raw = [s.time_to_first_token_ms for s in samples if s.time_to_first_token_ms is not None]
    total_raw = [s.total_duration_ms for s in samples if s.total_duration_ms is not None]

    tps = _remove_iqr_outliers(tps_raw) if remove_outliers else tps_raw
    ttft = _remove_iqr_outliers(ttft_raw) if remove_outliers else ttft_raw
    total = _remove_iqr_outliers(total_raw) if remove_outliers else total_raw

    def safe_stat(fn, data):
        if not data:
            return None
        try:
            return fn(data)
        except statistics.StatisticsError:
            return None

    return BenchmarkResult(
        model_id=model_id,
        server_name=server_name,
        runs=len(samples),
        mean_tps=safe_stat(statistics.mean, tps),
        median_tps=safe_stat(statistics.median, tps),
        p95_tps=_percentile(tps, 95),
        p99_tps=_percentile(tps, 99),
        stdev_tps=safe_stat(statistics.stdev, tps),
        min_tps=min(tps) if tps else None,
        max_tps=max(tps) if tps else None,
        mean_ttft_ms=safe_stat(statistics.mean, ttft),
        median_ttft_ms=safe_stat(statistics.median, ttft),
        p95_ttft_ms=_percentile(ttft, 95),
        p99_ttft_ms=_percentile(ttft, 99),
        stdev_ttft_ms=safe_stat(statistics.stdev, ttft),
        avg_prompt_tokens=statistics.mean([s.prompt_tokens for s in samples]) if samples else 0.0,
        avg_completion_tokens=statistics.mean([s.completion_tokens for s in samples]) if samples else 0.0,
        mean_total_ms=safe_stat(statistics.mean, total),
        p95_total_ms=_percentile(total, 95),
        raw_samples=samples,
    )
