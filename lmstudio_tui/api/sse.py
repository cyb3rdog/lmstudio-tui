from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

import httpx


class SSEClient:
    """Async SSE reader using httpx streaming. Reconnects with backoff on drop."""

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
