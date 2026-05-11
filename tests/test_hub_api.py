from __future__ import annotations

import pytest
import httpx
from pytest_httpx import HTTPXMock

from lmstudio_tui.api.hub import HubModel, search_hub

# ── Fixtures ──────────────────────────────────────────────────────────────────

HF_SEARCH_URL = "https://huggingface.co/api/models"

SAMPLE_RESPONSE = [
    {
        "id": "bartowski/Llama-3.1-8B-Instruct-GGUF",
        "downloads": 1_250_000,
        "likes": 4500,
        "tags": ["gguf", "llama", "text-generation"],
    },
    {
        "id": "lmstudio-community/Meta-Llama-3-8B-Instruct-GGUF",
        "downloads": 800_000,
        "likes": 2100,
        "tags": ["gguf"],
    },
    {
        "id": "TheBloke/Mistral-7B-Instruct-v0.2-GGUF",
        "downloads": 3_400_000,
        "likes": 9800,
        "tags": ["gguf", "mistral"],
    },
]


# ── HubModel unit tests ───────────────────────────────────────────────────────

class TestHubModel:
    def test_downloads_fmt_millions(self):
        m = HubModel(id="x", downloads=1_500_000)
        assert m.downloads_fmt == "1.5M"

    def test_downloads_fmt_thousands(self):
        m = HubModel(id="x", downloads=35_000)
        assert m.downloads_fmt == "35K"

    def test_downloads_fmt_small(self):
        m = HubModel(id="x", downloads=42)
        assert m.downloads_fmt == "42"

    def test_downloads_fmt_exactly_one_million(self):
        m = HubModel(id="x", downloads=1_000_000)
        assert m.downloads_fmt == "1.0M"

    def test_likes_fmt_thousands(self):
        m = HubModel(id="x", likes=4500)
        assert m.likes_fmt == "4.5K"

    def test_likes_fmt_small(self):
        m = HubModel(id="x", likes=99)
        assert m.likes_fmt == "99"

    def test_defaults_zero(self):
        m = HubModel(id="foo/bar")
        assert m.downloads == 0
        assert m.likes == 0
        assert m.tags == []


# ── search_hub integration tests (mocked HTTP) ───────────────────────────────

class TestSearchHub:
    async def test_returns_parsed_models(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(json=SAMPLE_RESPONSE)
        results = await search_hub("llama")
        assert len(results) == 3
        assert results[0].id == "bartowski/Llama-3.1-8B-Instruct-GGUF"
        assert results[0].downloads == 1_250_000
        assert results[2].id == "TheBloke/Mistral-7B-Instruct-v0.2-GGUF"

    async def test_empty_query_fetches_popular(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(json=SAMPLE_RESPONSE)
        results = await search_hub("")
        assert len(results) == 3

    async def test_filters_entries_without_id(self, httpx_mock: HTTPXMock):
        response = [
            {"id": "valid/model-GGUF", "downloads": 100, "likes": 5, "tags": []},
            {"downloads": 50, "likes": 1, "tags": []},          # no id
            {"id": "", "downloads": 200, "likes": 10, "tags": []},  # empty id
        ]
        httpx_mock.add_response(json=response)
        results = await search_hub("test")
        assert len(results) == 1
        assert results[0].id == "valid/model-GGUF"

    async def test_handles_null_downloads_and_likes(self, httpx_mock: HTTPXMock):
        response = [
            {"id": "foo/bar-GGUF", "downloads": None, "likes": None, "tags": None},
        ]
        httpx_mock.add_response(json=response)
        results = await search_hub("")
        assert results[0].downloads == 0
        assert results[0].likes == 0
        assert results[0].tags == []

    async def test_raises_on_http_error(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(status_code=503)
        with pytest.raises(httpx.HTTPStatusError):
            await search_hub("llama")

    async def test_raises_on_network_error(self, httpx_mock: HTTPXMock):
        httpx_mock.add_exception(httpx.ConnectError("Network unreachable"))
        with pytest.raises(httpx.ConnectError):
            await search_hub("llama")

    async def test_default_limit_is_60(self, httpx_mock: HTTPXMock):
        captured_url: list[str] = []

        def handler(req: httpx.Request) -> httpx.Response:
            captured_url.append(str(req.url))
            return httpx.Response(200, json=[])

        httpx_mock.add_callback(handler)
        await search_hub("")
        assert "limit=60" in captured_url[0]

    async def test_filter_is_always_gguf(self, httpx_mock: HTTPXMock):
        captured_url: list[str] = []

        def handler(req: httpx.Request) -> httpx.Response:
            captured_url.append(str(req.url))
            return httpx.Response(200, json=[])

        httpx_mock.add_callback(handler)
        await search_hub("mistral")
        assert "filter=gguf" in captured_url[0]

    async def test_search_term_included_when_provided(self, httpx_mock: HTTPXMock):
        captured_url: list[str] = []

        def handler(req: httpx.Request) -> httpx.Response:
            captured_url.append(str(req.url))
            return httpx.Response(200, json=[])

        httpx_mock.add_callback(handler)
        await search_hub("gemma")
        assert "search=gemma" in captured_url[0]

    async def test_no_search_param_when_query_empty(self, httpx_mock: HTTPXMock):
        captured_url: list[str] = []

        def handler(req: httpx.Request) -> httpx.Response:
            captured_url.append(str(req.url))
            return httpx.Response(200, json=[])

        httpx_mock.add_callback(handler)
        await search_hub("")
        assert "search=" not in captured_url[0]

    async def test_whitespace_only_query_treated_as_empty(self, httpx_mock: HTTPXMock):
        captured_url: list[str] = []

        def handler(req: httpx.Request) -> httpx.Response:
            captured_url.append(str(req.url))
            return httpx.Response(200, json=[])

        httpx_mock.add_callback(handler)
        await search_hub("   ")
        assert "search=" not in captured_url[0]

    async def test_sort_is_downloads_by_default(self, httpx_mock: HTTPXMock):
        captured_url: list[str] = []

        def handler(req: httpx.Request) -> httpx.Response:
            captured_url.append(str(req.url))
            return httpx.Response(200, json=[])

        httpx_mock.add_callback(handler)
        await search_hub("qwen")
        assert "sort=downloads" in captured_url[0]
