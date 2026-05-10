from __future__ import annotations

import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from itertools import cycle, islice

from ..api.client import LMStudioClient
from ..api.models import ChatCompletionRequest, ChatMessage, CompletionMetrics
from ..state.metrics_store import MetricSample, MetricsStore
from .analysis import BenchmarkResult, analyze
from .prompts import PromptLibrary


@dataclass
class BenchmarkSpec:
    model_id: str
    prompt_set: str = "mixed"
    runs: int = 10
    warmup: int = 2
    temperature: float = 0.0
    max_tokens: int = 256


class BenchmarkEngine:
    def __init__(self, client: LMStudioClient, metrics_store: MetricsStore, server_name: str) -> None:
        self._client = client
        self._store = metrics_store
        self._server = server_name

    async def run(self, spec: BenchmarkSpec) -> AsyncIterator[dict]:
        prompts = PromptLibrary.load(spec.prompt_set)
        prompt_cycle = list(islice(cycle(prompts), spec.warmup + spec.runs))

        # Warmup — discarded
        for i in range(spec.warmup):
            try:
                await self._infer(spec.model_id, prompt_cycle[i], spec)
            except Exception:
                pass

        samples: list[CompletionMetrics] = []
        for i in range(spec.runs):
            prompt = prompt_cycle[spec.warmup + i]
            try:
                metrics = await self._infer(spec.model_id, prompt, spec)
            except Exception as e:
                yield {"type": "error", "run": i + 1, "error": str(e)}
                continue

            samples.append(metrics)
            self._store.record(
                self._server,
                MetricSample.now(
                    model_id=spec.model_id,
                    tps=metrics.tokens_per_second,
                    ttft_ms=metrics.time_to_first_token_ms,
                    prompt_tokens=metrics.prompt_tokens,
                    completion_tokens=metrics.completion_tokens,
                ),
            )
            yield {"type": "sample", "run": i + 1, "metrics": metrics}

        result = analyze(samples, spec.model_id, self._server)
        yield {"type": "done", "result": result}

    async def _infer(self, model_id: str, prompt: str, spec: BenchmarkSpec) -> CompletionMetrics:
        req = ChatCompletionRequest(
            model=model_id,
            messages=[ChatMessage(role="user", content=prompt)],
            temperature=spec.temperature,
            max_tokens=spec.max_tokens,
        )
        _, metrics = await self._client.chat_completion(req)
        return metrics
