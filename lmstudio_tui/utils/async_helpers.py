from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

T = TypeVar("T")


async def retry_with_backoff(
    coro_factory: Callable[[], Coroutine[Any, Any, T]],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
) -> T:
    delay = base_delay
    last_exc: Exception = RuntimeError("No attempts made")
    for _ in range(max_retries):
        try:
            return await coro_factory()
        except Exception as e:
            last_exc = e
            await asyncio.sleep(delay)
            delay = min(delay * 2, max_delay)
    raise last_exc
