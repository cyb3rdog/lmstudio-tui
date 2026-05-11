from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from itertools import cycle, islice

from ..api.client import LMStudioClient
from ..api.models import ChatCompletionRequest, ChatMessage, CompletionMetrics
from ..state.metrics_store import MetricSample, MetricsStore
from .analysis import BenchmarkResult, analyze
from .prompts import PromptLibrary
from .tool_suite import ToolTestCase, get_tool_cases_for_mode


class BenchmarkMode:
    THROUGHPUT = "throughput"
    TOOL_CALLING = "tool_calling"
    LOAD_TIME = "load_time"
    PARALLEL = "parallel"


@dataclass
class BenchmarkSpec:
    model_id: str
    mode: str = BenchmarkMode.THROUGHPUT
    # Throughput mode
    prompt_set: str = "mixed"
    runs: int = 10
    warmup: int = 2
    temperature: float = 0.0
    max_tokens: int = 256
    # Tool calling mode
    tool_subset: str = "all"           # all | calculator | weather | string | search
    tool_runs_per_case: int = 1        # how many times to repeat each test case
    # Load time mode
    context_length: int | None = None  # context length when loading
    load_repetitions: int = 3          # measure load time this many times
    # Parallel mode
    parallel_slots: int = 4            # concurrent requests
    parallel_total: int = 20           # total requests across all slots


class BenchmarkEngine:
    def __init__(self, client: LMStudioClient, metrics_store: MetricsStore, server_name: str) -> None:
        self._client = client
        self._store = metrics_store
        self._server = server_name

    async def run(self, spec: BenchmarkSpec) -> AsyncIterator[dict]:
        """Dispatch to the appropriate mode runner."""
        if spec.mode == BenchmarkMode.THROUGHPUT:
            async for event in self._run_throughput(spec):
                yield event
        elif spec.mode == BenchmarkMode.TOOL_CALLING:
            async for event in self._run_tool_calling(spec):
                yield event
        elif spec.mode == BenchmarkMode.LOAD_TIME:
            async for event in self._run_load_time(spec):
                yield event
        elif spec.mode == BenchmarkMode.PARALLEL:
            async for event in self._run_parallel(spec):
                yield event

    # ── Throughput mode ───────────────────────────────────────────────────

    async def _run_throughput(self, spec: BenchmarkSpec) -> AsyncIterator[dict]:
        """Streaming inference with TTFT, TPOT, TPS measurement per run."""
        prompts = PromptLibrary.load(spec.prompt_set)
        prompt_cycle = list(islice(cycle(prompts), spec.warmup + spec.runs))

        for i in range(spec.warmup):
            try:
                await self._infer_streaming(spec.model_id, prompt_cycle[i], spec)
            except Exception:
                pass

        samples: list[CompletionMetrics] = []
        for i in range(spec.runs):
            prompt = prompt_cycle[spec.warmup + i]
            try:
                metrics = await self._infer_streaming(spec.model_id, prompt, spec)
            except Exception as e:
                yield {"type": "error", "run": i + 1, "error": str(e)}
                continue

            samples.append(metrics)
            self._record(metrics)
            yield {"type": "sample", "run": i + 1, "metrics": metrics}

        result = analyze(samples, spec.model_id, self._server, mode=spec.mode)
        yield {"type": "done", "result": result}

    async def _infer_streaming(self, model_id: str, prompt: str, spec: BenchmarkSpec) -> CompletionMetrics:
        req = ChatCompletionRequest(
            model=model_id,
            messages=[ChatMessage(role="user", content=prompt)],
            temperature=spec.temperature,
            max_tokens=spec.max_tokens,
        )
        _, metrics = await self._client.agentic_inference(req)
        return metrics

    # ── Tool calling mode ─────────────────────────────────────────────────

    async def _run_tool_calling(self, spec: BenchmarkSpec) -> AsyncIterator[dict]:
        """Send tool-calling prompts, evaluate name + arg correctness."""
        cases = get_tool_cases_for_mode(spec.tool_subset)
        if not cases:
            yield {"type": "error", "run": 0, "error": f"No test cases for subset '{spec.tool_subset}'"}
            return

        # Repeat each case tool_runs_per_case times
        test_runs: list[ToolTestCase] = []
        for _ in range(spec.tool_runs_per_case):
            test_runs.extend(cases)

        # Warmup — 1 pass through cases (discarded)
        for tc in cases[:spec.warmup]:
            try:
                await self._infer_tool(spec.model_id, tc, spec)
            except Exception:
                pass

        samples: list[CompletionMetrics] = []
        for i, tc in enumerate(test_runs):
            try:
                metrics = await self._infer_tool(spec.model_id, tc, spec)
            except Exception as e:
                yield {"type": "error", "run": i + 1, "error": str(e)}
                continue

            samples.append(metrics)
            self._record(metrics)
            yield {
                "type": "sample",
                "run": i + 1,
                "metrics": metrics,
                "tool_case": tc.description,
            }

        result = analyze(samples, spec.model_id, self._server, mode=spec.mode)
        yield {"type": "done", "result": result}

    async def _infer_tool(
        self, model_id: str, tc: ToolTestCase, spec: BenchmarkSpec
    ) -> CompletionMetrics:
        # Always send only the tool relevant to this test case (1 tool, not all 4).
        # The tool_subset filter in get_tool_cases_for_mode() controls which cases run.
        req = ChatCompletionRequest(
            model=model_id,
            messages=[ChatMessage(role="user", content=tc.prompt)],
            temperature=spec.temperature,
            max_tokens=spec.max_tokens,
            tools=[tc.tool_schema],
            tool_choice="auto",
        )
        _, metrics = await self._client.agentic_inference(
            req,
            expected_tool=tc.expected_tool,
            expected_args=tc.expected_args,
        )
        return metrics

    # ── Load time mode ────────────────────────────────────────────────────

    async def _run_load_time(self, spec: BenchmarkSpec) -> AsyncIterator[dict]:
        """Measure model load time across multiple unload→load→probe cycles.

        Each repetition:
        1. Unload the model (if loaded)
        2. Load the model — wall-clock timing
        3. Send a 1-token probe — measures first-inference latency
        """
        samples: list[CompletionMetrics] = []

        for i in range(spec.load_repetitions):
            # Unload if currently loaded
            try:
                models = await self._client.list_models()
                for m in models:
                    if m.id == spec.model_id and m.is_loaded and m.instance_id:
                        await self._client.unload_model(m.instance_id)
                        await asyncio.sleep(0.5)  # brief settle
                        break
            except Exception:
                pass

            try:
                _instance_id, metrics = await self._client.measure_load_time(
                    spec.model_id,
                    context_length=spec.context_length,
                )
            except Exception as e:
                yield {"type": "error", "run": i + 1, "error": str(e)}
                continue

            samples.append(metrics)
            yield {"type": "sample", "run": i + 1, "metrics": metrics}

        result = analyze(samples, spec.model_id, self._server, mode=spec.mode)
        yield {"type": "done", "result": result}

    # ── Parallel mode ─────────────────────────────────────────────────────

    async def _run_parallel(self, spec: BenchmarkSpec) -> AsyncIterator[dict]:
        """Fire spec.parallel_slots concurrent requests; repeat until parallel_total done.

        Measures: per-request TTFT (how long until first token arrives under load),
        per-request TPS, and aggregate throughput (total tokens / total wall time).
        """
        prompts = PromptLibrary.load(spec.prompt_set)
        prompt_cycle = list(islice(cycle(prompts), spec.parallel_total))

        semaphore = asyncio.Semaphore(spec.parallel_slots)
        samples: list[CompletionMetrics] = []
        run_counter = 0
        t_wall_start = time.perf_counter()

        # Event queue so we can yield results as they come in
        result_queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=spec.parallel_total)

        async def _task(prompt: str, idx: int) -> None:
            async with semaphore:
                req = ChatCompletionRequest(
                    model=spec.model_id,
                    messages=[ChatMessage(role="user", content=prompt)],
                    temperature=spec.temperature,
                    max_tokens=spec.max_tokens,
                )
                try:
                    _, metrics = await self._client.agentic_inference(req)
                    await result_queue.put({"type": "sample", "run": idx + 1, "metrics": metrics})
                except Exception as e:
                    await result_queue.put({"type": "error", "run": idx + 1, "error": str(e)})

        tasks = [
            asyncio.create_task(_task(prompt_cycle[i], i))
            for i in range(spec.parallel_total)
        ]

        # Drain results as tasks complete
        completed = 0
        while completed < spec.parallel_total:
            event = await result_queue.get()
            completed += 1
            if event["type"] == "sample":
                samples.append(event["metrics"])
                self._record(event["metrics"])
            yield event

        await asyncio.gather(*tasks, return_exceptions=True)

        t_wall_ms = (time.perf_counter() - t_wall_start) * 1000.0
        total_tokens = sum(s.completion_tokens for s in samples)
        parallel_tps = (total_tokens / t_wall_ms * 1000.0) if t_wall_ms > 0 and total_tokens > 0 else None

        result = analyze(samples, spec.model_id, self._server, mode=spec.mode)
        result.parallel_tps = parallel_tps
        yield {"type": "done", "result": result}

    # ── helpers ───────────────────────────────────────────────────────────

    def _record(self, metrics: CompletionMetrics) -> None:
        self._store.record(
            self._server,
            MetricSample.now(
                model_id=metrics.model_id,
                tps=metrics.tokens_per_second,
                ttft_ms=metrics.time_to_first_token_ms,
                prompt_tokens=metrics.prompt_tokens,
                completion_tokens=metrics.completion_tokens,
            ),
        )
