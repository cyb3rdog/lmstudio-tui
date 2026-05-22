from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

import httpx


class SSEClient:
    """Server-Sent Events client for LM Studio log streaming (planned feature).

This class is defined but not yet used. LM Studio's SSE log endpoint
(/api/v1/logs) currently returns 404 on the v1 API. The client.py module
uses an inline `_stream_raw()` method for chat completions instead.

Planned for: Phase 8 — live log stream display in Monitor screen.
When LM Studio adds a working SSE endpoint, wire this in via
LMStudioClient.llmstudio_stream_events().
"""

    def __init__(self, http: httpx.AsyncClient, endpoint: str) -> None:
        self._http = http
        self._endpoint = endpoint

    async def stream_events(self) -> AsyncIterator[dict[str, Any]]:
        delay = 1.0
        while True:
            try:
                async with self._http.stream("GET", self._endpoint) as response:
                    delay = 1.0  # reset backoff on successful connect
                    async for line in response.aiter_lines():
                        if line.startswith("data:"):
                            payload = line[5:].strip()
                            if payload and payload != "[DONE]":
                                try:
                                    yield json.loads(payload)
                                except json.JSONDecodeError:
                                    yield {"raw": payload}
            except (httpx.ConnectError, httpx.RemoteProtocolError):
                await asyncio.sleep(delay)
                delay = min(delay * 2, 30.0)
            except httpx.TimeoutException:
                await asyncio.sleep(delay)
                delay = min(delay * 2, 30.0)
            except asyncio.CancelledError:
                return
