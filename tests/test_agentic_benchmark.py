from __future__ import annotations

import json

import pytest

from lmstudio_tui.api.client import LMStudioClient
from lmstudio_tui.api.models import CompletionMetrics
from lmstudio_tui.benchmark.analysis import (
    BenchmarkResult,
    analyze,
    detect_winners,
)
from lmstudio_tui.benchmark.tool_suite import (
    ALL_TOOLS,
    TOOL_TEST_CASES,
    get_tool_cases_for_mode,
)


# ── Tool suite tests ──────────────────────────────────────────────────────


class TestToolSuite:
    def test_all_tools_have_required_fields(self):
        for tool in ALL_TOOLS:
            assert tool["type"] == "function"
            fn = tool["function"]
            assert "name" in fn
            assert "description" in fn
            assert "parameters" in fn
            assert "properties" in fn["parameters"]

    def test_tool_test_cases_nonempty(self):
        assert len(TOOL_TEST_CASES) >= 8

    def test_each_case_has_prompt_and_expected(self):
        for tc in TOOL_TEST_CASES:
            assert tc.prompt
            assert tc.expected_tool
            assert isinstance(tc.expected_args, dict)

    def test_get_tool_cases_all(self):
        assert get_tool_cases_for_mode("all") == TOOL_TEST_CASES

    def test_get_tool_cases_calculator(self):
        cases = get_tool_cases_for_mode("calculator")
        assert all(tc.expected_tool == "calculator" for tc in cases)
        assert len(cases) >= 2

    def test_get_tool_cases_weather(self):
        cases = get_tool_cases_for_mode("weather")
        assert all(tc.expected_tool == "get_weather" for tc in cases)

    def test_get_tool_cases_string(self):
        cases = get_tool_cases_for_mode("string")
        assert all(tc.expected_tool == "string_transform" for tc in cases)

    def test_get_tool_cases_search(self):
        cases = get_tool_cases_for_mode("search")
        assert all(tc.expected_tool == "web_search" for tc in cases)

    def test_unknown_subset_returns_empty(self):
        assert get_tool_cases_for_mode("nonexistent") == []


# ── Tool arg scoring tests ────────────────────────────────────────────────


class TestScoreToolArgs:
    def test_perfect_match_returns_1(self):
        expected = {"operation": "multiply", "a": 47, "b": 13}
        actual = {"operation": "multiply", "a": 47, "b": 13}
        assert LMStudioClient._score_tool_args(expected, actual) == pytest.approx(1.0)

    def test_empty_expected_returns_1(self):
        assert LMStudioClient._score_tool_args({}, {"extra": "key"}) == pytest.approx(1.0)

    def test_empty_actual_returns_0(self):
        assert LMStudioClient._score_tool_args({"key": "val"}, {}) == pytest.approx(0.0)

    def test_missing_key_gives_no_credit(self):
        expected = {"a": 1, "b": 2}
        actual = {"a": 1}
        score = LMStudioClient._score_tool_args(expected, actual)
        assert score == pytest.approx(0.5)  # 1 of 2 keys present, perfect match

    def test_type_mismatch_gives_half_credit(self):
        expected = {"a": 10}
        actual = {"a": "10"}  # str instead of int
        score = LMStudioClient._score_tool_args(expected, actual)
        assert score == pytest.approx(0.5)

    def test_string_case_insensitive(self):
        expected = {"city": "Paris"}
        actual = {"city": "paris"}
        assert LMStudioClient._score_tool_args(expected, actual) == pytest.approx(1.0)

    def test_numeric_within_1pct_full_credit(self):
        expected = {"a": 100.0}
        actual = {"a": 100.5}  # 0.5% off
        assert LMStudioClient._score_tool_args(expected, actual) == pytest.approx(1.0)

    def test_numeric_beyond_1pct_half_credit(self):
        expected = {"a": 100.0}
        actual = {"a": 105.0}  # 5% off
        assert LMStudioClient._score_tool_args(expected, actual) == pytest.approx(0.5)

    def test_score_capped_at_1(self):
        expected = {"a": 1}
        actual = {"a": 1, "b": 2}  # extra key — should not exceed 1.0
        assert LMStudioClient._score_tool_args(expected, actual) <= 1.0


# ── Agentic BenchmarkResult fields ───────────────────────────────────────


def make_agentic_sample(
    tps: float = 40.0,
    ttft_ms: float = 100.0,
    tpot_ms: float = 25.0,
    total_ms: float = 2000.0,
    tool_called: bool = True,
    tool_name_correct: bool | None = True,
    tool_args_score: float | None = 0.9,
    reasoning_tokens: int = 0,
    load_time_ms: float | None = None,
    was_jit: bool = False,
) -> CompletionMetrics:
    return CompletionMetrics(
        model_id="test",
        tokens_per_second=tps,
        time_to_first_token_ms=ttft_ms,
        tpot_ms=tpot_ms,
        total_duration_ms=total_ms,
        prompt_tokens=50,
        completion_tokens=80,
        reasoning_tokens=reasoning_tokens,
        tool_called=tool_called,
        tool_name_correct=tool_name_correct,
        tool_args_score=tool_args_score,
        load_time_ms=load_time_ms,
        was_jit=was_jit,
    )


class TestAgenticAnalyze:
    def test_tool_call_rate_all_called(self):
        samples = [make_agentic_sample(tool_called=True) for _ in range(5)]
        result = analyze(samples, "m", "s", mode="tool_calling")
        assert result.tool_call_rate == pytest.approx(1.0)

    def test_tool_call_rate_none_called(self):
        samples = [make_agentic_sample(tool_called=False, tool_name_correct=None) for _ in range(4)]
        result = analyze(samples, "m", "s", mode="tool_calling")
        assert result.tool_call_rate == pytest.approx(0.0)

    def test_tool_call_rate_mixed(self):
        samples = [
            make_agentic_sample(tool_called=True),
            make_agentic_sample(tool_called=True),
            make_agentic_sample(tool_called=False, tool_name_correct=None),
        ]
        result = analyze(samples, "m", "s", mode="tool_calling")
        assert result.tool_call_rate == pytest.approx(2 / 3)

    def test_tool_name_accuracy(self):
        samples = [
            make_agentic_sample(tool_name_correct=True),
            make_agentic_sample(tool_name_correct=True),
            make_agentic_sample(tool_name_correct=False),
        ]
        result = analyze(samples, "m", "s", mode="tool_calling")
        assert result.tool_name_accuracy == pytest.approx(2 / 3)

    def test_mean_tool_args_score(self):
        samples = [make_agentic_sample(tool_args_score=0.8) for _ in range(3)]
        result = analyze(samples, "m", "s", mode="tool_calling")
        assert result.mean_tool_args_score == pytest.approx(0.8)

    def test_tpot_stats_calculated(self):
        samples = [make_agentic_sample(tpot_ms=25.0) for _ in range(5)]
        result = analyze(samples, "m", "s", mode="throughput")
        assert result.mean_tpot_ms == pytest.approx(25.0)
        assert result.median_tpot_ms == pytest.approx(25.0)

    def test_reasoning_tokens_avg(self):
        samples = [make_agentic_sample(reasoning_tokens=100) for _ in range(3)]
        result = analyze(samples, "m", "s", mode="throughput")
        assert result.avg_reasoning_tokens == pytest.approx(100.0)

    def test_load_time_stats(self):
        samples = [make_agentic_sample(load_time_ms=3000.0) for _ in range(4)]
        result = analyze(samples, "m", "s", mode="load_time")
        assert result.mean_load_time_ms == pytest.approx(3000.0)

    def test_jit_detected_when_any_sample_is_jit(self):
        samples = [
            make_agentic_sample(was_jit=True),
            make_agentic_sample(was_jit=False),
        ]
        result = analyze(samples, "m", "s", mode="load_time")
        assert result.jit_detected is True

    def test_jit_not_detected_when_none(self):
        samples = [make_agentic_sample(was_jit=False) for _ in range(3)]
        result = analyze(samples, "m", "s", mode="load_time")
        assert result.jit_detected is False

    def test_mode_stored_in_result(self):
        samples = [make_agentic_sample() for _ in range(2)]
        result = analyze(samples, "m", "s", mode="parallel")
        assert result.mode == "parallel"


# ── Winner detection ──────────────────────────────────────────────────────


def make_result(
    model_id: str,
    mean_tps: float | None = None,
    mean_ttft_ms: float | None = None,
    tool_name_accuracy: float | None = None,
    mean_load_time_ms: float | None = None,
) -> BenchmarkResult:
    return BenchmarkResult(
        model_id=model_id,
        server_name="s",
        runs=5,
        mean_tps=mean_tps,
        mean_ttft_ms=mean_ttft_ms,
        tool_name_accuracy=tool_name_accuracy,
        mean_load_time_ms=mean_load_time_ms,
    )


class TestDetectWinners:
    def test_highest_tps_wins(self):
        results = [
            make_result("a", mean_tps=40.0),
            make_result("b", mean_tps=55.0),
            make_result("c", mean_tps=30.0),
        ]
        detect_winners(results)
        assert results[1].winner_tps is True
        assert results[0].winner_tps is False
        assert results[2].winner_tps is False

    def test_lowest_ttft_wins(self):
        results = [
            make_result("a", mean_ttft_ms=200.0),
            make_result("b", mean_ttft_ms=80.0),
        ]
        detect_winners(results)
        assert results[1].winner_ttft is True
        assert results[0].winner_ttft is False

    def test_highest_tool_accuracy_wins(self):
        results = [
            make_result("a", tool_name_accuracy=0.6),
            make_result("b", tool_name_accuracy=0.9),
        ]
        detect_winners(results)
        assert results[1].winner_tool_accuracy is True

    def test_lowest_load_time_wins(self):
        results = [
            make_result("a", mean_load_time_ms=5000.0),
            make_result("b", mean_load_time_ms=2000.0),
        ]
        detect_winners(results)
        assert results[1].winner_load_time is True

    def test_single_result_no_winner_set(self):
        results = [make_result("a", mean_tps=40.0)]
        detect_winners(results)
        # Single result: no winner flag set (need ≥2 to compare)
        assert results[0].winner_tps is False

    def test_none_metrics_skipped(self):
        results = [
            make_result("a", mean_tps=None),
            make_result("b", mean_tps=40.0),
        ]
        detect_winners(results)
        assert results[1].winner_tps is True
        assert results[0].winner_tps is False
