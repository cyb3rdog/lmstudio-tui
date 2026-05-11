from __future__ import annotations

import heapq
import time
from collections import deque
from dataclasses import dataclass


@dataclass
class MetricSample:
    timestamp: float
    tokens_per_second: float | None
    time_to_first_token_ms: float | None
    prompt_tokens: int
    completion_tokens: int
    model_id: str

    @classmethod
    def now(
        cls,
        model_id: str,
        tps: float | None,
        ttft_ms: float | None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ) -> "MetricSample":
        return cls(
            timestamp=time.time(),
            tokens_per_second=tps,
            time_to_first_token_ms=ttft_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model_id=model_id,
        )


class MetricsStore:
    """Ring-buffer (deque maxlen=WINDOW) per (server_name, model_id).

    Feeds sparklines and recent-request tables on the Live Monitor screen.
    """

    WINDOW = 120

    def __init__(self) -> None:
        self._data: dict[tuple[str, str], deque[MetricSample]] = {}

    def _key(self, server: str, model_id: str) -> tuple[str, str]:
        return (server, model_id)

    def record(self, server: str, sample: MetricSample) -> None:
        key = self._key(server, sample.model_id)
        if key not in self._data:
            self._data[key] = deque(maxlen=self.WINDOW)
        self._data[key].append(sample)

    def get_samples(self, server: str, model_id: str) -> list[MetricSample]:
        return list(self._data.get(self._key(server, model_id), []))

    def get_tps_series(self, server: str, model_id: str) -> list[float]:
        return [s.tokens_per_second for s in self.get_samples(server, model_id) if s.tokens_per_second is not None]

    def get_ttft_series(self, server: str, model_id: str) -> list[float]:
        return [s.time_to_first_token_ms for s in self.get_samples(server, model_id) if s.time_to_first_token_ms is not None]

    def latest(self, server: str, model_id: str) -> MetricSample | None:
        samples = self._data.get(self._key(server, model_id))
        return samples[-1] if samples else None

    def all_recent(self, server: str, limit: int = 50) -> list[MetricSample]:
        """Return the newest `limit` samples across all models for a server.

        Iterates each per-model deque once; uses heapq.nlargest for O(n log k)
        time where k = limit and n = total samples (bounded by WINDOW per model).
        """
        candidates: list[MetricSample] = []
        for (srv, _), dq in self._data.items():
            if srv == server:
                candidates.extend(dq)
        # heapq.nlargest returns the k largest items; negate timestamp for newest-first.
        if len(candidates) <= limit:
            candidates.reverse()
            return candidates
        return heapq.nlargest(limit, candidates, key=lambda s: s.timestamp)

    def clear_server(self, server: str) -> None:
        """Remove all metric keys for a given server.

        Call this when disconnecting so stale keys don't accumulate in memory.
        """
        self._data = {k: v for k, v in self._data.items() if k[0] != server}
