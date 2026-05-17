from __future__ import annotations

from dataclasses import dataclass, field

import httpx

HF_API_BASE = "https://huggingface.co/api"


@dataclass
class HubModel:
    id: str
    downloads: int = 0
    likes: int = 0
    tags: list[str] = field(default_factory=list)

    @property
    def downloads_fmt(self) -> str:
        d = self.downloads
        if d >= 1_000_000:
            return f"{d / 1_000_000:.1f}M"
        if d >= 1_000:
            return f"{d / 1_000:.0f}K"
        return str(d)

    @property
    def likes_fmt(self) -> str:
        k = self.likes
        if k >= 1_000:
            return f"{k / 1_000:.1f}K"
        return str(k)


_GGUF_QUANT_PREFERENCE = [
    "q4_k_m", "q4_k_s", "q5_k_m", "q5_k_s", "q4_0", "q8_0", "q3_k_m",
    "q2_k", "fp16", "f16",
]


async def list_gguf_files(repo_id: str) -> list[str]:
    """Return GGUF filenames for a HuggingFace repo, sorted by preference.

    Fetches the repo metadata and extracts .gguf siblings. Returns basenames.
    """
    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
        resp = await client.get(f"{HF_API_BASE}/models/{repo_id}")
        resp.raise_for_status()
        data = resp.json()

    siblings: list[dict] = data.get("siblings", [])
    gguf_files = [s["rfilename"] for s in siblings if s.get("rfilename", "").endswith(".gguf")]

    def _sort_key(fname: str) -> int:
        lower = fname.lower()
        for i, pattern in enumerate(_GGUF_QUANT_PREFERENCE):
            if pattern in lower:
                return i
        return len(_GGUF_QUANT_PREFERENCE)

    return sorted(gguf_files, key=_sort_key)


async def search_hub(
    query: str,
    limit: int = 60,
    sort: str = "downloads",
) -> list[HubModel]:
    """Search HuggingFace Hub for GGUF models.

    With an empty query, returns the most-downloaded GGUF models overall.
    Raises httpx.HTTPError on network/HTTP failures.
    """
    params: dict = {
        "filter": "gguf",
        "sort": sort,
        "direction": -1,
        "limit": limit,
    }
    if query.strip():
        params["search"] = query.strip()

    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
        resp = await client.get(f"{HF_API_BASE}/models", params=params)
        resp.raise_for_status()
        data: list[dict] = resp.json()

    return [
        HubModel(
            id=m.get("id", ""),
            downloads=m.get("downloads", 0) or 0,
            likes=m.get("likes", 0) or 0,
            tags=m.get("tags", []) or [],
        )
        for m in data
        if m.get("id")
    ]
