from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx

from ..config.models import ServerConfig
from . import exceptions as exc
from .models import (
    ChatCompletionRequest,
    CompletionMetrics,
    DownloadStatus,
    LoadRequest,
    LoadResponse,
    ModelInfo,
    ModelsResponse,
    UnloadRequest,
)


class LMStudioClient:
    def __init__(self, config: ServerConfig) -> None:
        self._config = config
        self._http = httpx.AsyncClient(
            base_url=config.endpoint,
            headers=config.headers(),
            timeout=httpx.Timeout(120.0, connect=5.0),
        )

    async def close(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> "LMStudioClient":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    # ── helpers ──────────────────────────────────────────────────────────────

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code == 401:
            raise exc.AuthError("Invalid or missing API key")
        if response.status_code == 403:
            raise exc.AuthError("Forbidden")
        if response.status_code >= 400:
            try:
                detail = response.json().get("error", {}).get("message", response.text)
            except Exception:
                detail = response.text
            raise exc.APIError(response.status_code, detail)

    async def _get(self, path: str) -> Any:
        try:
            r = await self._http.get(path)
            self._raise_for_status(r)
            return r.json()
        except httpx.ConnectError as e:
            raise exc.ConnectionError(str(e)) from e
        except httpx.TimeoutException as e:
            raise exc.TimeoutError(str(e)) from e

    async def _post(self, path: str, body: Any) -> Any:
        try:
            r = await self._http.post(path, json=body)
            self._raise_for_status(r)
            return r.json()
        except httpx.ConnectError as e:
            raise exc.ConnectionError(str(e)) from e
        except httpx.TimeoutException as e:
            raise exc.TimeoutError(str(e)) from e

    async def _stream_raw(self, path: str, body: dict) -> AsyncIterator[dict]:
        """Yield raw SSE JSON dicts from a streaming POST. Raises typed exceptions."""
        try:
            async with self._http.stream("POST", path, json=body) as response:
                self._raise_for_status(response)
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if payload == "[DONE]":
                        break
                    try:
                        yield json.loads(payload)
                    except json.JSONDecodeError:
                        continue
        except httpx.ConnectError as e:
            raise exc.ConnectionError(str(e)) from e
        except httpx.TimeoutException as e:
            raise exc.TimeoutError(str(e)) from e

    @staticmethod
    def _extract_metrics(data: dict, model_id: str, total_ms: float) -> CompletionMetrics:
        """Extract performance metrics from a non-streaming LM Studio response.

        LM Studio's stats{} is always empty — all timing is wall-clock.
        """
        usage = data.get("usage", {})
        prompt_toks = usage.get("prompt_tokens", 0)
        completion_toks = usage.get("completion_tokens", 0)

        tps: float | None = None
        if total_ms > 0 and completion_toks > 0:
            tps = (completion_toks / total_ms) * 1000.0

        return CompletionMetrics(
            model_id=model_id,
            tokens_per_second=tps,
            time_to_first_token_ms=None,
            total_duration_ms=total_ms,
            prompt_tokens=prompt_toks,
            completion_tokens=completion_toks,
        )

    @staticmethod
    def _score_tool_args(expected: dict, actual: dict) -> float:
        """Return 0.0–1.0 fuzzy similarity between expected and actual tool args.

        Scoring:
        - +1/N for each expected key present in actual
        - Half credit when value types match but values differ
        - Full credit when values match (string: case-insensitive; numeric: within 1%)
        """
        if not expected:
            return 1.0
        if not actual:
            return 0.0

        score = 0.0
        per_key = 1.0 / len(expected)

        for key, exp_val in expected.items():
            if key not in actual:
                continue
            act_val = actual[key]
            if type(exp_val) != type(act_val):
                score += per_key * 0.5
                continue
            if isinstance(exp_val, str) and exp_val.lower() == act_val.lower():
                score += per_key
            elif isinstance(exp_val, (int, float)):
                if exp_val == 0:
                    score += per_key if act_val == 0 else per_key * 0.5
                elif abs(exp_val - act_val) / abs(exp_val) <= 0.01:
                    score += per_key
                else:
                    score += per_key * 0.5
            elif exp_val == act_val:
                score += per_key
            else:
                score += per_key * 0.5

        return min(score, 1.0)

    # ── health ────────────────────────────────────────────────────────────────

    async def ping(self) -> float:
        """Return round-trip latency in ms, or raise ConnectionError."""
        start = time.perf_counter()
        await self._get("/api/v1/models")
        return (time.perf_counter() - start) * 1000

    # ── models ────────────────────────────────────────────────────────────────

    async def list_models(self) -> list[ModelInfo]:
        raw = await self._get("/api/v1/models")
        return ModelsResponse.from_raw(raw).model_list

    async def load_model(self, request: LoadRequest) -> str:
        body: dict[str, Any] = {"model": request.model}
        # LM Studio v1 rejects gpu_layers with "Unrecognized key(s)".
        if request.context_length and request.context_length > 0:
            body["context_length"] = request.context_length
        data = await self._post("/api/v1/models/load", body)
        return LoadResponse.model_validate(data).instance_id

    async def unload_model(self, instance_id: str) -> None:
        await self._post("/api/v1/models/unload", UnloadRequest(instance_id=instance_id).model_dump())

    async def download_model(self, model_id: str) -> None:
        await self._post("/api/v1/models/download", {"model": model_id})

    async def get_download_status(self) -> DownloadStatus | None:
        try:
            data = await self._get("/api/v1/models/download/status")
            return DownloadStatus.model_validate(data)
        except exc.APIError:
            return None

    # ── inference ─────────────────────────────────────────────────────────────

    async def chat_completion(
        self, request: ChatCompletionRequest
    ) -> tuple[str, CompletionMetrics]:
        """Non-streaming chat completion. Returns (text, metrics)."""
        req = request.model_copy(update={"stream": False})
        t0 = time.perf_counter()
        data = await self._post("/v1/chat/completions", req.model_dump(exclude_none=True))
        total_ms = (time.perf_counter() - t0) * 1000

        text = data["choices"][0]["message"]["content"]
        metrics = self._extract_metrics(data, request.model, total_ms)
        return text, metrics

    async def chat_completion_stream(
        self, request: ChatCompletionRequest
    ) -> AsyncIterator[str]:
        """Streaming chat completion; yields text delta chunks."""
        req = request.model_copy(update={"stream": True})
        body = req.model_dump(exclude_none=True)
        async for chunk in self._stream_raw("/v1/chat/completions", body):
            try:
                delta = chunk["choices"][0]["delta"].get("content", "")
                if delta:
                    yield delta
            except (KeyError, IndexError):
                continue

    async def agentic_inference(
        self,
        request: ChatCompletionRequest,
        *,
        expected_tool: str | None = None,
        expected_args: dict | None = None,
    ) -> tuple[str, CompletionMetrics]:
        """Streaming inference with full agentic metrics.

        Measures TTFT (wall-clock to first content/tool token), TPOT, reasoning
        tokens (from reasoning_content deltas), and tool call correctness.

        Returns (full_text_or_tool_result_summary, CompletionMetrics).
        """
        req = request.model_copy(update={"stream": True})
        body = req.model_dump(exclude_none=True)

        t0 = time.perf_counter()
        t_first: float | None = None

        content_parts: list[str] = []
        reasoning_parts: list[str] = []
        # index → {id, name, arguments_str}
        tool_calls_acc: dict[int, dict[str, str]] = {}
        completion_tokens = 0
        prompt_tokens = 0

        async for chunk in self._stream_raw("/v1/chat/completions", body):
            now = time.perf_counter()
            try:
                choice = chunk["choices"][0]
                delta = choice.get("delta", {})

                # Reasoning content (extended field — reasoning models)
                reasoning_delta = delta.get("reasoning_content", "")
                if reasoning_delta:
                    if t_first is None:
                        t_first = now
                    reasoning_parts.append(reasoning_delta)

                # Regular content
                content_delta = delta.get("content", "")
                if content_delta:
                    if t_first is None:
                        t_first = now
                    content_parts.append(content_delta)

                # Tool call deltas — accumulate across chunks
                tool_delta_list = delta.get("tool_calls", [])
                for td in tool_delta_list:
                    idx = td.get("index", 0)
                    if t_first is None:
                        t_first = now
                    if idx not in tool_calls_acc:
                        tool_calls_acc[idx] = {"id": "", "name": "", "arguments": ""}
                    acc = tool_calls_acc[idx]
                    if td.get("id"):
                        acc["id"] = td["id"]
                    fn = td.get("function", {})
                    if fn.get("name"):
                        acc["name"] = fn["name"]
                    if fn.get("arguments"):
                        acc["arguments"] += fn["arguments"]

            except (KeyError, IndexError):
                pass

            # Token counts from usage field (appears in final chunk on some servers)
            usage = chunk.get("usage") or {}
            if usage.get("prompt_tokens"):
                prompt_tokens = usage["prompt_tokens"]
            if usage.get("completion_tokens"):
                completion_tokens = usage["completion_tokens"]

        t_end = time.perf_counter()
        total_ms = (t_end - t0) * 1000.0
        ttft_ms = (t_first - t0) * 1000.0 if t_first is not None else None

        # LM Studio often omits usage from streaming chunks. Fall back to counting
        # content delta chunks — each SSE event is approximately one token.
        if completion_tokens == 0 and content_parts:
            completion_tokens = len(content_parts)

        # TPOT: time per output token (excluding first token latency)
        tpot_ms: float | None = None
        if ttft_ms is not None and completion_tokens > 1 and total_ms > ttft_ms:
            tpot_ms = (total_ms - ttft_ms) / (completion_tokens - 1)

        # TPS via wall clock (fallback since LM Studio stats{} is always empty)
        tps: float | None = None
        if total_ms > 0 and completion_tokens > 0:
            tps = (completion_tokens / total_ms) * 1000.0

        # reasoning_tokens: chunk count, not real token count — LM Studio's /v1/chat/completions
        # does not split completion_tokens_details for reasoning. This is a proxy only.
        reasoning_tokens = len(reasoning_parts)

        # Tool call evaluation
        tool_called = bool(tool_calls_acc)
        tool_name_correct: bool | None = None
        tool_args_score: float | None = None

        if expected_tool is not None:
            called_names = [acc["name"] for acc in tool_calls_acc.values() if acc["name"]]
            tool_name_correct = expected_tool in called_names
            if tool_name_correct and expected_args is not None:
                # Find the matching call
                for acc in tool_calls_acc.values():
                    if acc["name"] == expected_tool:
                        try:
                            actual_args = json.loads(acc["arguments"]) if acc["arguments"] else {}
                        except json.JSONDecodeError:
                            actual_args = {}
                        tool_args_score = self._score_tool_args(expected_args, actual_args)
                        break

        full_text = "".join(content_parts)
        # Summarise tool calls in output text when no content was returned
        if tool_calls_acc and not full_text:
            parts = []
            for acc in tool_calls_acc.values():
                parts.append(f"{acc['name']}({acc['arguments']})")
            full_text = " | ".join(parts)

        metrics = CompletionMetrics(
            model_id=request.model,
            tokens_per_second=tps,
            time_to_first_token_ms=ttft_ms,
            tpot_ms=tpot_ms,
            total_duration_ms=total_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            reasoning_tokens=reasoning_tokens,
            tool_called=tool_called,
            tool_name_correct=tool_name_correct,
            tool_args_score=tool_args_score,
        )
        return full_text, metrics

    async def measure_load_time(
        self,
        model_id: str,
        context_length: int | None = None,
        *,
        probe_prompt: str = "Hi",
    ) -> tuple[str, CompletionMetrics]:
        """Load a model and measure JIT load + first-inference time.

        Sends a minimal probe request and returns (instance_id, metrics) with
        load_time_ms and was_jit populated. The model must NOT be loaded yet.

        Uses LM Studio's load_time_seconds from the load response as the
        authoritative load metric (excludes HTTP overhead). Falls back to
        wall-clock if the server returns 0.
        """
        from .models import ChatMessage

        # Detect whether model is currently loaded
        models = await self.list_models()
        already_loaded = any(m.id == model_id and m.is_loaded for m in models)

        body: dict[str, Any] = {"model": model_id}
        if context_length and context_length > 0:
            body["context_length"] = context_length

        t_wall = time.perf_counter()
        data = await self._post("/api/v1/models/load", body)
        wall_ms = (time.perf_counter() - t_wall) * 1000.0

        load_resp = LoadResponse.model_validate(data)
        instance_id = load_resp.instance_id
        # Prefer server's measurement (pure GPU/CPU load, excludes HTTP latency)
        load_ms = load_resp.load_time_seconds * 1000.0 if load_resp.load_time_seconds > 0 else wall_ms

        chat_req = ChatCompletionRequest(
            model=model_id,
            messages=[ChatMessage(role="user", content=probe_prompt)],
            max_tokens=1,
            temperature=0.0,
        )
        _, metrics = await self.agentic_inference(chat_req)
        metrics.load_time_ms = load_ms
        metrics.was_jit = not already_loaded
        return instance_id, metrics
