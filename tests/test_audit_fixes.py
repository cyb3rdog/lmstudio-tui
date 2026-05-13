"""Tests for the audit fixes: MetricsStore, download system, benchmark, and config."""

from __future__ import annotations

import asyncio
import time

from lmstudio_tui.state.metrics_store import MetricSample, MetricsStore
from lmstudio_tui.api.client import LMStudioClient  # noqa: E402
from lmstudio_tui.api.models import ChatCompletionRequest, ChatMessage, CompletionMetrics
from lmstudio_tui.benchmark.tool_suite import (
    TOOL_TEST_CASES,
    ToolTestCase,
    get_tool_cases_for_mode,
)


# ── MetricSample ────────────────────────────────────────────────────────────────

class TestMetricSampleNow:
    def test_timestamp_is_set(self) -> None:
        before = time.time()
        sample = MetricSample.now("model-1", tps=10.0, ttft_ms=50.0, prompt_tokens=5, completion_tokens=20)
        after = time.time()
        assert before <= sample.timestamp <= after

    def test_fields_forwarded(self) -> None:
        sample = MetricSample.now(
            model_id="test-model",
            tps=15.5,
            ttft_ms=123.4,
            prompt_tokens=10,
            completion_tokens=50,
        )
        assert sample.model_id == "test-model"
        assert sample.tokens_per_second == 15.5
        assert sample.time_to_first_token_ms == 123.4
        assert sample.prompt_tokens == 10
        assert sample.completion_tokens == 50


# ── MetricsStore recording ──────────────────────────────────────────────────────

class TestMetricsStoreRecord:
    def test_records_sample_for_server_model(self) -> None:
        store = MetricsStore()
        store.record("srv1", MetricSample.now("model-a", tps=10.0, ttft_ms=50.0))
        assert len(store.get_samples("srv1", "model-a")) == 1

    def test_same_key_appends(self) -> None:
        store = MetricsStore()
        store.record("srv1", MetricSample.now("model-a", tps=10.0, ttft_ms=50.0))
        store.record("srv1", MetricSample.now("model-a", tps=11.0, ttft_ms=51.0))
        assert len(store.get_samples("srv1", "model-a")) == 2

    def test_different_servers_separate(self) -> None:
        store = MetricsStore()
        store.record("srv1", MetricSample.now("model-a", tps=10.0, ttft_ms=50.0))
        store.record("srv2", MetricSample.now("model-a", tps=20.0, ttft_ms=60.0))
        assert store.get_samples("srv1", "model-a")[0].tokens_per_second == 10.0
        assert store.get_samples("srv2", "model-a")[0].tokens_per_second == 20.0

    def test_maxlen_enforced(self) -> None:
        store = MetricsStore()
        for _ in range(200):
            store.record("srv1", MetricSample.now("model-a", tps=10.0, ttft_ms=50.0))
        assert len(store.get_samples("srv1", "model-a")) == 120  # default MetricsStore window


# ── MetricsStore series ────────────────────────────────────────────────────────

class TestMetricsStoreSeries:
    def test_get_tps_series_filters_none(self) -> None:
        store = MetricsStore()
        store.record("srv", MetricSample.now("m", tps=10.0, ttft_ms=None))
        store.record("srv", MetricSample.now("m", tps=None, ttft_ms=50.0))
        store.record("srv", MetricSample.now("m", tps=20.0, ttft_ms=None))
        tps = store.get_tps_series("srv", "m")
        assert tps == [10.0, 20.0]

    def test_get_ttft_series_filters_none(self) -> None:
        store = MetricsStore()
        store.record("srv", MetricSample.now("m", tps=10.0, ttft_ms=50.0))
        store.record("srv", MetricSample.now("m", tps=10.0, ttft_ms=None))
        store.record("srv", MetricSample.now("m", tps=10.0, ttft_ms=60.0))
        ttft = store.get_ttft_series("srv", "m")
        assert ttft == [50.0, 60.0]

    def test_latest_returns_newest(self) -> None:
        store = MetricsStore()
        time.sleep(0.01)
        s1 = MetricSample.now("m", tps=1.0, ttft_ms=10.0)
        time.sleep(0.01)
        s2 = MetricSample.now("m", tps=2.0, ttft_ms=20.0)
        store.record("srv", s1)
        store.record("srv", s2)
        latest = store.latest("srv", "m")
        assert latest is s2


# ── MetricsStore all_recent ────────────────────────────────────────────────────

class TestMetricsStoreAllRecent:
    def test_returns_newest_first(self) -> None:
        store = MetricsStore()
        time.sleep(0.01)
        s1 = MetricSample.now("m", tps=1.0, ttft_ms=10.0)
        time.sleep(0.01)
        s2 = MetricSample.now("m", tps=2.0, ttft_ms=20.0)
        time.sleep(0.01)
        s3 = MetricSample.now("m", tps=3.0, ttft_ms=30.0)
        store.record("srv", s1)
        store.record("srv", s2)
        store.record("srv", s3)
        recent = store.all_recent("srv", limit=10)
        assert [s.tokens_per_second for s in recent] == [3.0, 2.0, 1.0]

    def test_limit_enforced(self) -> None:
        store = MetricsStore()
        for i in range(100):
            store.record("srv", MetricSample.now("m", tps=float(i), ttft_ms=10.0))
        recent = store.all_recent("srv", limit=5)
        assert len(recent) == 5
        assert [s.tokens_per_second for s in recent] == [99.0, 98.0, 97.0, 96.0, 95.0]

    def test_across_multiple_models(self) -> None:
        store = MetricsStore()
        time.sleep(0.01)
        s1 = MetricSample.now("model-a", tps=1.0, ttft_ms=10.0)
        time.sleep(0.01)
        s2 = MetricSample.now("model-b", tps=2.0, ttft_ms=20.0)
        time.sleep(0.01)
        s3 = MetricSample.now("model-a", tps=3.0, ttft_ms=30.0)
        time.sleep(0.01)
        s4 = MetricSample.now("model-c", tps=4.0, ttft_ms=40.0)
        store.record("srv", s1)
        store.record("srv", s2)
        store.record("srv", s3)
        store.record("srv", s4)
        recent = store.all_recent("srv", limit=3)
        assert [s.tokens_per_second for s in recent] == [4.0, 3.0, 2.0]

    def test_ignores_other_servers(self) -> None:
        store = MetricsStore()
        store.record("srv1", MetricSample.now("m", tps=1.0, ttft_ms=10.0))
        store.record("srv2", MetricSample.now("m", tps=2.0, ttft_ms=20.0))
        recent = store.all_recent("srv1", limit=10)
        assert len(recent) == 1
        assert recent[0].tokens_per_second == 1.0

    def test_empty_when_no_data(self) -> None:
        store = MetricsStore()
        assert store.all_recent("srv1", limit=10) == []


# ── MetricsStore clear_server ──────────────────────────────────────────────────

class TestMetricsStoreClearServer:
    def test_removes_all_keys_for_server(self) -> None:
        store = MetricsStore()
        store.record("srv1", MetricSample.now("m1", tps=1.0, ttft_ms=10.0))
        store.record("srv1", MetricSample.now("m2", tps=2.0, ttft_ms=20.0))
        store.record("srv2", MetricSample.now("m3", tps=3.0, ttft_ms=30.0))
        store.clear_server("srv1")
        assert store.get_samples("srv1", "m1") == []
        assert store.get_samples("srv1", "m2") == []
        # srv2 should be untouched
        assert len(store.get_samples("srv2", "m3")) == 1


# ── MetricsStore edge cases ────────────────────────────────────────────────────

class TestMetricsStoreEdgeCases:
    def test_clear_empty_server_does_not_raise(self) -> None:
        store = MetricsStore()
        store.clear_server("nonexistent")  # must not raise
        assert True

    def test_latest_returns_none_for_missing(self) -> None:
        store = MetricsStore()
        assert store.latest("srv", "m") is None

    def test_get_samples_empty_for_missing(self) -> None:
        store = MetricsStore()
        assert store.get_samples("srv", "nonexistent") == []

    def test_get_tps_series_empty_for_missing(self) -> None:
        store = MetricsStore()
        assert store.get_tps_series("srv", "nonexistent") == []

    def test_get_ttft_series_empty_for_missing(self) -> None:
        store = MetricsStore()
        assert store.get_ttft_series("srv", "nonexistent") == []

    def test_record_none_tps_still_stored(self) -> None:
        store = MetricsStore()
        s = MetricSample.now("m", tps=None, ttft_ms=50.0)
        store.record("srv", s)
        # sample is stored even if tps is None
        assert len(store.get_samples("srv", "m")) == 1

    def test_record_none_ttft_still_stored(self) -> None:
        store = MetricsStore()
        s = MetricSample.now("m", tps=10.0, ttft_ms=None)
        store.record("srv", s)
        assert len(store.get_samples("srv", "m")) == 1

    def test_all_recent_with_limit_zero(self) -> None:
        store = MetricsStore()
        store.record("srv", MetricSample.now("m", tps=1.0, ttft_ms=10.0))
        result = store.all_recent("srv", limit=0)
        assert result == []

    def test_multiple_servers_isolated(self) -> None:
        store = MetricsStore()
        store.record("srv1", MetricSample.now("m1", tps=1.0, ttft_ms=10.0))
        store.record("srv2", MetricSample.now("m1", tps=2.0, ttft_ms=20.0))
        store.record("srv2", MetricSample.now("m2", tps=3.0, ttft_ms=30.0))
        # srv1 should have 1 sample
        assert len(store.all_recent("srv1", limit=10)) == 1
        # srv2 should have 2 samples
        assert len(store.all_recent("srv2", limit=10)) == 2

    def test_clear_server_removes_all_models_for_that_server(self) -> None:
        store = MetricsStore()
        store.record("srv1", MetricSample.now("m1", tps=1.0, ttft_ms=10.0))
        store.record("srv1", MetricSample.now("m2", tps=2.0, ttft_ms=20.0))
        store.record("srv2", MetricSample.now("m3", tps=3.0, ttft_ms=30.0))
        store.clear_server("srv1")
        assert store.all_recent("srv1", limit=10) == []
        # srv2 should be untouched
        assert len(store.all_recent("srv2", limit=10)) == 1

    def test_all_recent_order_newest_first(self) -> None:
        store = MetricsStore()
        for i in range(5):
            time.sleep(0.001)
            store.record("srv", MetricSample.now("m", tps=float(i), ttft_ms=10.0))
        recent = store.all_recent("srv", limit=10)
        tps_values = [s.tokens_per_second for s in recent]
        assert tps_values == sorted(tps_values, reverse=True)

    def test_windows_maxlen_per_model(self) -> None:
        store = MetricsStore()
        for i in range(120 + 50):
            store.record("srv", MetricSample.now("m", tps=float(i), ttft_ms=10.0))
        assert len(store.get_samples("srv", "m")) == 120  # default MetricsStore window


# ── Config defaults ────────────────────────────────────────────────────────────

class TestConfigDefaults:
    def test_poll_interval_default(self) -> None:
        from lmstudio_tui.config.models import UIConfig
        cfg = UIConfig()
        assert cfg.poll_interval_s == 3.0

    def test_benchmark_defaults(self) -> None:
        from lmstudio_tui.config.models import BenchmarkConfig
        cfg = BenchmarkConfig()
        assert cfg.default_samples == 10
        assert cfg.warmup_runs == 2
        assert cfg.export_dir == "~/.lmstudio-tui/benchmarks"


class TestServerConfig:
    def test_headers_empty_when_no_api_key(self) -> None:
        from lmstudio_tui.config.models import ServerConfig
        cfg = ServerConfig()
        assert cfg.headers() == {}

    def test_headers_bearer_when_api_key_set(self) -> None:
        from lmstudio_tui.config.models import ServerConfig
        cfg = ServerConfig(api_key="secret")
        assert cfg.headers() == {"Authorization": "Bearer secret"}


# ── CompletionMetrics defaults ─────────────────────────────────────────────────

class TestCompletionMetricsDefaults:
    def test_prompt_tokens_default_zero(self) -> None:
        from lmstudio_tui.api.models import CompletionMetrics
        m = CompletionMetrics()
        assert m.prompt_tokens == 0

    def test_tool_called_default_false(self) -> None:
        from lmstudio_tui.api.models import CompletionMetrics
        m = CompletionMetrics()
        assert m.tool_called is False

    def test_was_jit_default_false(self) -> None:
        from lmstudio_tui.api.models import CompletionMetrics
        m = CompletionMetrics()
        assert m.was_jit is False

    def test_reasoning_tokens_default_zero(self) -> None:
        from lmstudio_tui.api.models import CompletionMetrics
        m = CompletionMetrics()
        assert m.reasoning_tokens == 0

    def test_tokens_per_second_default_none(self) -> None:
        from lmstudio_tui.api.models import CompletionMetrics
        m = CompletionMetrics()
        assert m.tokens_per_second is None

    def test_tpot_ms_default_none(self) -> None:
        from lmstudio_tui.api.models import CompletionMetrics
        m = CompletionMetrics()
        assert m.tpot_ms is None

    def test_total_duration_ms_default_none(self) -> None:
        from lmstudio_tui.api.models import CompletionMetrics
        m = CompletionMetrics()
        assert m.total_duration_ms is None

    def test_tool_name_correct_default_none(self) -> None:
        # None = "not evaluated" — different from False = "wrong"
        from lmstudio_tui.api.models import CompletionMetrics
        m = CompletionMetrics()
        assert m.tool_name_correct is None

    def test_tool_args_score_default_none(self) -> None:
        from lmstudio_tui.api.models import CompletionMetrics
        m = CompletionMetrics()
        assert m.tool_args_score is None

    def test_load_time_ms_default_none(self) -> None:
        from lmstudio_tui.api.models import CompletionMetrics
        m = CompletionMetrics()
        assert m.load_time_ms is None


# ── BenchmarkSpec defaults ─────────────────────────────────────────────────────

class TestBenchmarkSpecDefaults:
    def test_throughput_defaults(self) -> None:
        from lmstudio_tui.benchmark.engine import BenchmarkMode, BenchmarkSpec
        spec = BenchmarkSpec(model_id="test")
        assert spec.mode == BenchmarkMode.THROUGHPUT
        assert spec.runs == 10
        assert spec.warmup == 2
        assert spec.temperature == 0.0
        assert spec.max_tokens == 256
        assert spec.tool_subset == "all"

    def test_parallel_defaults(self) -> None:
        from lmstudio_tui.benchmark.engine import BenchmarkMode, BenchmarkSpec
        spec = BenchmarkSpec(model_id="test", mode=BenchmarkMode.PARALLEL)
        assert spec.parallel_slots == 4
        assert spec.parallel_total == 20

    def test_load_time_defaults(self) -> None:
        from lmstudio_tui.benchmark.engine import BenchmarkMode, BenchmarkSpec
        spec = BenchmarkSpec(model_id="test", mode=BenchmarkMode.LOAD_TIME)
        assert spec.load_repetitions == 3
        assert spec.context_length is None


# ── Tool suite ─────────────────────────────────────────────────────────────────

class TestToolSuiteGetCases:
    def test_all_returns_all_cases(self) -> None:
        cases = get_tool_cases_for_mode("all")
        assert len(cases) == len(TOOL_TEST_CASES)
        assert cases is TOOL_TEST_CASES

    def test_calculator_subset(self) -> None:
        cases = get_tool_cases_for_mode("calculator")
        assert all(tc.expected_tool == "calculator" for tc in cases)

    def test_weather_subset(self) -> None:
        cases = get_tool_cases_for_mode("weather")
        assert all(tc.expected_tool == "get_weather" for tc in cases)

    def test_string_subset(self) -> None:
        cases = get_tool_cases_for_mode("string")
        assert all(tc.expected_tool == "string_transform" for tc in cases)

    def test_search_subset(self) -> None:
        cases = get_tool_cases_for_mode("search")
        assert all(tc.expected_tool == "web_search" for tc in cases)

    def test_unknown_subset_filters_by_name(self) -> None:
        # Unknown subset is treated as a tool name filter — returns nothing
        # because no test case has expected_tool == "unknown".
        cases = get_tool_cases_for_mode("unknown")
        assert cases == []


class TestToolSuiteEdgeCases:
    def test_empty_string_returns_empty(self) -> None:
        # Empty string is not "all" — treated as unknown tool name → []
        cases = get_tool_cases_for_mode("")
        assert cases == []

    def test_case_has_expected_fields(self) -> None:
        for tc in TOOL_TEST_CASES:
            assert tc.prompt, "ToolTestCase must have a prompt"
            assert tc.expected_tool, "ToolTestCase must have an expected_tool"
            assert tc.tool_schema, "ToolTestCase must have a tool_schema"
            # Name is nested at schema['function']['name'] per OpenAI tool format
            func = tc.tool_schema.get("function", {})
            assert "name" in func, "tool_schema['function'] must have a 'name' key"

    def test_tool_schema_has_name_and_description(self) -> None:
        for tc in TOOL_TEST_CASES:
            schema = tc.tool_schema
            assert "type" in schema
            assert schema["type"] == "function"
            func = schema.get("function", {})
            assert "name" in func
            assert "description" in func

    def test_expected_args_optional(self) -> None:
        for tc in TOOL_TEST_CASES:
            assert tc.expected_args is None or isinstance(tc.expected_args, dict)

    def test_empty_string_returns_empty(self) -> None:
        # Empty string is not "all" — treated as unknown tool name → []
        cases = get_tool_cases_for_mode("")
        assert cases == []


# ── Tool argument scoring ──────────────────────────────────────────────────────

class TestScoreToolArgs:
    def test_empty_expected_returns_full_score(self) -> None:
        score = LMStudioClient._score_tool_args({}, {"a": 1})
        assert score == 1.0

    def test_empty_actual_returns_zero(self) -> None:
        score = LMStudioClient._score_tool_args({"a": 1}, {})
        assert score == 0.0

    def test_string_case_insensitive(self) -> None:
        score = LMStudioClient._score_tool_args({"city": "Paris"}, {"city": "paris"})
        assert score == 1.0

    def test_numeric_within_one_percent(self) -> None:
        # Use float in both to avoid type-mismatch half-credit.
        # In real use, JSON-parsed values are always float, so this is the
        # representative case: both are float, and within 1%.
        score = LMStudioClient._score_tool_args({"a": 100.0}, {"a": 100.5})
        assert score == 1.0

    def test_numeric_outside_one_percent_half_credit(self) -> None:
        score = LMStudioClient._score_tool_args({"a": 100.0}, {"a": 110.0})
        assert score == 0.5

    def test_wrong_type_half_credit(self) -> None:
        score = LMStudioClient._score_tool_args({"a": "hi"}, {"a": 123})
        assert score == 0.5

    def test_capped_at_one(self) -> None:
        score = LMStudioClient._score_tool_args({"a": 1, "b": 2}, {"a": 1, "b": 2})
        assert score == 1.0


# ── ChatCompletionRequest model_dump ─────────────────────────────────────────

class TestChatCompletionRequestModelDump:
    def test_exclude_none_removes_nulls(self) -> None:
        req = ChatCompletionRequest(
            model="test",
            messages=[ChatMessage(role="user", content="hi")],
            temperature=0.0,
        )
        dumped = req.model_dump(exclude_none=True)
        # stream=False, max_tokens=None, top_p=None, etc. should not appear
        assert "stream" not in dumped or dumped.get("stream") is False
        assert "max_tokens" not in dumped

    def test_tools_included_when_set(self) -> None:
        req = ChatCompletionRequest(
            model="test",
            messages=[ChatMessage(role="user", content="hi")],
            tools=[{"type": "function", "function": {"name": "test", "description": "t"}}],
        )
        dumped = req.model_dump(exclude_none=True)
        assert "tools" in dumped
        assert len(dumped["tools"]) == 1


class TestChatMessage:
    def test_content_can_be_string(self) -> None:
        msg = ChatMessage(role="user", content="hello")
        assert msg.content == "hello"

    def test_content_can_be_list(self) -> None:
        msg = ChatMessage(role="user", content=[{"type": "text", "text": "hello"}])
        assert isinstance(msg.content, list)

    def test_tool_call_id_optional(self) -> None:
        msg = ChatMessage(role="tool", content="result", tool_call_id="call_123")
        assert msg.tool_call_id == "call_123"
