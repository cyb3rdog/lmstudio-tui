from __future__ import annotations

import statistics
from dataclasses import dataclass, field

from ..api.models import CompletionMetrics


@dataclass
class BenchmarkResult:
    model_id: str
    server_name: str
    runs: int
    mode: str = "throughput"  # throughput | tool_calling | load_time | parallel
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
    # TPOT (time-per-output-token, streaming only)
    mean_tpot_ms: float | None = None
    median_tpot_ms: float | None = None
    # Tokens
    avg_prompt_tokens: float = 0.0
    avg_completion_tokens: float = 0.0
    avg_reasoning_tokens: float = 0.0
    # Total latency
    mean_total_ms: float | None = None
    p95_total_ms: float | None = None
    # Tool calling (mode=tool_calling only)
    tool_call_rate: float | None = None        # fraction of runs that called any tool
    tool_name_accuracy: float | None = None    # fraction with correct tool name
    mean_tool_args_score: float | None = None  # 0.0–1.0 average arg similarity
    # Load time (mode=load_time only)
    mean_load_time_ms: float | None = None
    p95_load_time_ms: float | None = None
    jit_detected: bool = False
    # Parallel (mode=parallel only)
    parallel_tps: float | None = None          # aggregate TPS across all concurrent slots
    # Winner flags — set by detect_winners()
    winner_tps: bool = False
    winner_ttft: bool = False
    winner_tool_accuracy: bool = False
    winner_load_time: bool = False
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
    mode: str = "throughput",
) -> BenchmarkResult:
    def _vals(attr: str) -> list[float]:
        return [getattr(s, attr) for s in samples if getattr(s, attr) is not None]

    def _clean(data: list[float]) -> list[float]:
        return _remove_iqr_outliers(data) if remove_outliers else data

    def safe_stat(fn, data):
        if not data:
            return None
        try:
            return fn(data)
        except statistics.StatisticsError:
            return None

    tps = _clean(_vals("tokens_per_second"))
    ttft = _clean(_vals("time_to_first_token_ms"))
    tpot = _clean(_vals("tpot_ms"))
    total = _clean(_vals("total_duration_ms"))
    load = _clean(_vals("load_time_ms"))

    # Tool calling stats
    tc_samples = [s for s in samples if s.tool_called is not None]
    tc_name_correct = [s for s in samples if s.tool_name_correct is not None]
    tc_args = [s.tool_args_score for s in samples if s.tool_args_score is not None]

    tool_call_rate: float | None = None
    tool_name_accuracy: float | None = None
    mean_tool_args_score: float | None = None

    if tc_samples:
        tool_call_rate = sum(1 for s in tc_samples if s.tool_called) / len(tc_samples)
    if tc_name_correct:
        tool_name_accuracy = sum(1 for s in tc_name_correct if s.tool_name_correct) / len(tc_name_correct)
    if tc_args:
        mean_tool_args_score = statistics.mean(tc_args)

    # JIT detection
    jit_detected = any(s.was_jit for s in samples)

    return BenchmarkResult(
        model_id=model_id,
        server_name=server_name,
        runs=len(samples),
        mode=mode,
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
        mean_tpot_ms=safe_stat(statistics.mean, tpot),
        median_tpot_ms=safe_stat(statistics.median, tpot),
        avg_prompt_tokens=statistics.mean([s.prompt_tokens for s in samples]) if samples else 0.0,
        avg_completion_tokens=statistics.mean([s.completion_tokens for s in samples]) if samples else 0.0,
        avg_reasoning_tokens=statistics.mean([s.reasoning_tokens for s in samples]) if samples else 0.0,
        mean_total_ms=safe_stat(statistics.mean, total),
        p95_total_ms=_percentile(total, 95),
        tool_call_rate=tool_call_rate,
        tool_name_accuracy=tool_name_accuracy,
        mean_tool_args_score=mean_tool_args_score,
        mean_load_time_ms=safe_stat(statistics.mean, load),
        p95_load_time_ms=_percentile(load, 95),
        jit_detected=jit_detected,
        raw_samples=samples,
    )


def detect_winners(results: list[BenchmarkResult]) -> list[BenchmarkResult]:
    """Mark the best model per metric category. Modifies results in-place."""
    if len(results) < 2:
        return results

    # Higher TPS is better
    tps_vals = [(r.mean_tps, i) for i, r in enumerate(results) if r.mean_tps is not None]
    if tps_vals:
        best_i = max(tps_vals, key=lambda x: x[0])[1]
        results[best_i].winner_tps = True

    # Lower TTFT is better
    ttft_vals = [(r.mean_ttft_ms, i) for i, r in enumerate(results) if r.mean_ttft_ms is not None]
    if ttft_vals:
        best_i = min(ttft_vals, key=lambda x: x[0])[1]
        results[best_i].winner_ttft = True

    # Higher tool accuracy is better
    acc_vals = [(r.tool_name_accuracy, i) for i, r in enumerate(results) if r.tool_name_accuracy is not None]
    if acc_vals:
        best_i = max(acc_vals, key=lambda x: x[0])[1]
        results[best_i].winner_tool_accuracy = True

    # Lower load time is better
    load_vals = [(r.mean_load_time_ms, i) for i, r in enumerate(results) if r.mean_load_time_ms is not None]
    if load_vals:
        best_i = min(load_vals, key=lambda x: x[0])[1]
        results[best_i].winner_load_time = True

    return results
