from __future__ import annotations

import pytest

from lmstudio_tui.api.models import CompletionMetrics
from lmstudio_tui.benchmark.analysis import (
    BenchmarkResult,
    _percentile,
    _remove_iqr_outliers,
    analyze,
)


def make_sample(tps: float | None = 40.0, ttft_ms: float | None = 100.0,
                total_ms: float | None = 2000.0) -> CompletionMetrics:
    return CompletionMetrics(
        model_id="test",
        tokens_per_second=tps,
        time_to_first_token_ms=ttft_ms,
        total_duration_ms=total_ms,
        prompt_tokens=50,
        completion_tokens=80,
    )


class TestPercentile:
    def test_median_of_sorted_list(self):
        data = [1.0, 2.0, 3.0, 4.0, 5.0]
        assert _percentile(data, 50) == pytest.approx(3.0)

    def test_p0_is_minimum(self):
        data = [10.0, 20.0, 30.0]
        assert _percentile(data, 0) == pytest.approx(10.0)

    def test_p100_is_maximum(self):
        data = [10.0, 20.0, 30.0]
        assert _percentile(data, 100) == pytest.approx(30.0)

    def test_p95_on_small_dataset(self):
        data = list(range(1, 21))  # 1..20
        result = _percentile(data, 95)
        assert result is not None
        assert 19.0 <= result <= 20.0

    def test_empty_list_returns_none(self):
        assert _percentile([], 50) is None

    def test_single_element(self):
        assert _percentile([42.0], 50) == pytest.approx(42.0)

    def test_interpolates_between_values(self):
        data = [0.0, 10.0]
        # p50 of [0, 10] should be exactly 5
        assert _percentile(data, 50) == pytest.approx(5.0)


class TestRemoveIqrOutliers:
    def test_removes_high_outlier(self):
        data = [40.0, 41.0, 40.5, 42.0, 41.5, 200.0]  # 200 is an outlier
        cleaned = _remove_iqr_outliers(data)
        assert 200.0 not in cleaned

    def test_removes_low_outlier(self):
        data = [1.0, 40.0, 41.0, 40.5, 42.0, 41.5]  # 1.0 is an outlier
        cleaned = _remove_iqr_outliers(data)
        assert 1.0 not in cleaned

    def test_clean_data_unchanged(self):
        data = [40.0, 41.0, 40.5, 42.0, 41.5]
        cleaned = _remove_iqr_outliers(data)
        assert len(cleaned) == len(data)

    def test_small_list_returned_unchanged(self):
        data = [1.0, 2.0, 3.0]
        cleaned = _remove_iqr_outliers(data)
        assert cleaned == data

    def test_empty_list_returns_empty(self):
        assert _remove_iqr_outliers([]) == []


class TestAnalyze:
    def test_returns_benchmark_result(self):
        samples = [make_sample() for _ in range(5)]
        result = analyze(samples, "test-model", "server")
        assert isinstance(result, BenchmarkResult)

    def test_mean_tps_calculated(self):
        samples = [make_sample(tps=40.0) for _ in range(5)]
        result = analyze(samples, "test-model", "server")
        assert result.mean_tps == pytest.approx(40.0)

    def test_mean_ttft_calculated(self):
        samples = [make_sample(ttft_ms=100.0) for _ in range(5)]
        result = analyze(samples, "test-model", "server")
        assert result.mean_ttft_ms == pytest.approx(100.0)

    def test_stdev_tps_calculated_with_variance(self):
        samples = [make_sample(tps=float(v)) for v in [30.0, 40.0, 50.0, 35.0, 45.0]]
        result = analyze(samples, "test-model", "server")
        assert result.stdev_tps is not None
        assert result.stdev_tps > 0

    def test_min_max_tps(self):
        samples = [make_sample(tps=float(v)) for v in [30.0, 40.0, 50.0]]
        result = analyze(samples, "test-model", "server", remove_outliers=False)
        assert result.min_tps == pytest.approx(30.0)
        assert result.max_tps == pytest.approx(50.0)

    def test_empty_samples_returns_none_stats(self):
        result = analyze([], "test-model", "server")
        assert result.mean_tps is None
        assert result.mean_ttft_ms is None
        assert result.runs == 0

    def test_single_sample_works(self):
        result = analyze([make_sample(tps=42.0)], "test-model", "server")
        assert result.mean_tps == pytest.approx(42.0)
        assert result.stdev_tps is None  # can't compute stdev of 1 item

    def test_raw_samples_stored(self):
        samples = [make_sample() for _ in range(3)]
        result = analyze(samples, "test-model", "server")
        assert len(result.raw_samples) == 3

    def test_token_averages_calculated(self):
        samples = [make_sample() for _ in range(4)]
        result = analyze(samples, "test-model", "server")
        assert result.avg_prompt_tokens == pytest.approx(50.0)
        assert result.avg_completion_tokens == pytest.approx(80.0)

    def test_samples_with_none_tps_excluded_from_stats(self):
        samples = [make_sample(tps=40.0), make_sample(tps=None), make_sample(tps=40.0)]
        result = analyze(samples, "test-model", "server")
        assert result.mean_tps == pytest.approx(40.0)

    def test_remove_outliers_false_keeps_all(self):
        data = [40.0] * 4 + [200.0]  # 200 would normally be removed
        samples = [make_sample(tps=v) for v in data]
        result = analyze(samples, "test-model", "server", remove_outliers=False)
        assert result.max_tps == pytest.approx(200.0)
