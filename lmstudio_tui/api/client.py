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
            timeout=httpx.Timeout(60.0, connect=5.0),
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

    @staticmethod
    def _extract_metrics(data: dict, model_id: str, total_ms: float) -> CompletionMetrics:
        """Extract performance metrics from a LM Studio chat/completion response.

        LM Studio v1 puts perf data in a top-level 'stats' key:
          stats.tokens_per_second    (float)
          stats.time_to_first_token  (float, seconds)
          stats.time_to_generate     (float, seconds)

        Older / OpenAI-compat responses may omit stats entirely; we fall back to
        wall-clock total_ms in that case and leave tps/ttft as None.
        """
        usage = data.get("usage", {})
        stats = data.get("stats", {})

        tps: float | None = stats.get("tokens_per_second")
        # LM Studio returns TTFT in seconds; convert to ms
        ttft_s: float | None = stats.get("time_to_first_token")
        ttft_ms = ttft_s * 1000.0 if ttft_s is not None else None

        return CompletionMetrics(
            model_id=model_id,
            tokens_per_second=tps,
            time_to_first_token_ms=ttft_ms,
            total_duration_ms=total_ms,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
        )

    # ── health ────────────────────────────────────────────────────────────────

    async def ping(self) -> float:
        """Return round-trip latency in ms, or raise ConnectionError."""
        start = time.perf_counter()
        await self._get("/v1/models")
        return (time.perf_counter() - start) * 1000

    # ── models ────────────────────────────────────────────────────────────────

    async def list_models(self) -> list[ModelInfo]:
        data = await self._get("/api/v1/models")
        return ModelsResponse.model_validate(data).data

    async def load_model(self, request: LoadRequest) -> str:
        body: dict[str, Any] = {"model": request.model}
        if request.gpu_layers is not None:
            body["gpu_layers"] = request.gpu_layers
        if request.context_length is not None:
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
        try:
            async with self._http.stream(
                "POST",
                "/v1/chat/completions",
                json=req.model_dump(exclude_none=True),
            ) as response:
                self._raise_for_status(response)
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if payload == "[DONE]":
                        break
                    try:
                        chunk = json.loads(payload)
                        delta = chunk["choices"][0]["delta"].get("content", "")
                        if delta:
                            yield delta
                    except (json.JSONDecodeError, KeyError):
                        continue
        except httpx.ConnectError as e:
            raise exc.ConnectionError(str(e)) from e
        except httpx.TimeoutException as e:
            raise exc.TimeoutError(str(e)) from e
