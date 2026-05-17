from __future__ import annotations

import json

import httpx
import pytest
import pytest_asyncio

from lmstudio_tui.api import exceptions as exc
from lmstudio_tui.api.client import LMStudioClient
from lmstudio_tui.api.models import ChatCompletionRequest, ChatMessage, LoadRequest
from lmstudio_tui.config.models import ServerConfig


def make_client(transport: httpx.MockTransport) -> LMStudioClient:
    cfg = ServerConfig(name="test", endpoint="http://localhost:1234")
    client = LMStudioClient(cfg)
    client._http = httpx.AsyncClient(
        base_url=cfg.endpoint,
        transport=transport,
        timeout=httpx.Timeout(5.0),
    )
    return client


def json_response(data: dict, status: int = 200) -> httpx.Response:
    return httpx.Response(status, json=data)


class TestPing:
    async def test_ping_returns_positive_float(self, lmstudio_models_response):
        transport = httpx.MockTransport(
            lambda req: json_response(lmstudio_models_response)
        )
        client = make_client(transport)
        ms = await client.ping()
        assert isinstance(ms, float)
        assert ms >= 0

    async def test_ping_uses_api_v1_endpoint(self, lmstudio_models_response):
        captured: list[str] = []

        def handler(req: httpx.Request) -> httpx.Response:
            captured.append(req.url.path)
            return json_response(lmstudio_models_response)

        client = make_client(httpx.MockTransport(handler))
        await client.ping()
        assert captured[0] == "/api/v1/models"

    async def test_ping_raises_connection_error_on_network_failure(self):
        def handler(req: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("refused")

        client = make_client(httpx.MockTransport(handler))
        with pytest.raises(exc.ConnectionError):
            await client.ping()


class TestListModels:
    async def test_returns_parsed_model_list(self, lmstudio_models_response):
        transport = httpx.MockTransport(
            lambda req: json_response(lmstudio_models_response)
        )
        client = make_client(transport)
        models = await client.list_models()
        assert len(models) == 3

    async def test_401_raises_auth_error(self):
        transport = httpx.MockTransport(
            lambda req: json_response({"error": {"message": "Unauthorized"}}, 401)
        )
        client = make_client(transport)
        with pytest.raises(exc.AuthError):
            await client.list_models()

    async def test_500_raises_api_error(self):
        transport = httpx.MockTransport(
            lambda req: json_response({"error": {"message": "Internal error"}}, 500)
        )
        client = make_client(transport)
        with pytest.raises(exc.APIError) as exc_info:
            await client.list_models()
        assert exc_info.value.status_code == 500


class TestLoadModel:
    async def test_sends_model_field(self):
        captured: list[dict] = []

        def handler(req: httpx.Request) -> httpx.Response:
            captured.append(json.loads(req.content))
            return json_response({
                "instance_id": "mymodel:0",
                "model": "mymodel",
                "type": "llm",
                "load_time_seconds": 1.5,
                "status": "loaded",
            })

        client = make_client(httpx.MockTransport(handler))
        req = LoadRequest(model="mymodel")
        instance_id = await client.load_model(req)
        assert instance_id == "mymodel:0"
        assert captured[0]["model"] == "mymodel"

    async def test_sends_gpu_layers_when_set(self):
        """gpu_layers should be forwarded to the API when provided."""
        captured: list[dict] = []

        def handler(req: httpx.Request) -> httpx.Response:
            captured.append(json.loads(req.content))
            return json_response({
                "instance_id": "m:0",
                "model": "m",
                "type": "llm",
                "load_time_seconds": 0.0,
                "status": "loaded",
            })

        client = make_client(httpx.MockTransport(handler))
        req = LoadRequest(model="m", gpu_layers=32)
        await client.load_model(req)
        assert captured[0]["gpu_layers"] == 32

    async def test_omits_gpu_layers_when_none(self):
        """gpu_layers should not be sent when not set."""
        captured: list[dict] = []

        def handler(req: httpx.Request) -> httpx.Response:
            captured.append(json.loads(req.content))
            return json_response({
                "instance_id": "m:0",
                "model": "m",
                "type": "llm",
                "load_time_seconds": 0.0,
                "status": "loaded",
            })

        client = make_client(httpx.MockTransport(handler))
        req = LoadRequest(model="m", gpu_layers=None)
        await client.load_model(req)
        assert "gpu_layers" not in captured[0]

    async def test_sends_context_length_when_set(self):
        captured: list[dict] = []

        def handler(req: httpx.Request) -> httpx.Response:
            captured.append(json.loads(req.content))
            return json_response({
                "instance_id": "m:0",
                "model": "m",
                "type": "llm",
                "load_time_seconds": 0.0,
                "status": "loaded",
            })

        client = make_client(httpx.MockTransport(handler))
        req = LoadRequest(model="m", context_length=4096)
        await client.load_model(req)
        assert captured[0]["context_length"] == 4096


class TestExtractMetrics:
    def test_calculates_wall_clock_tps(self, chat_completion_response):
        metrics = LMStudioClient._extract_metrics(
            chat_completion_response, "test-model", 1000.0
        )
        # 8 completion tokens / 1000ms = 8 t/s
        assert metrics.tokens_per_second == pytest.approx(8.0)

    def test_zero_completion_tokens_gives_none_tps(self):
        data = {
            "usage": {"prompt_tokens": 10, "completion_tokens": 0},
            "stats": {},
        }
        metrics = LMStudioClient._extract_metrics(data, "m", 500.0)
        assert metrics.tokens_per_second is None

    def test_ttft_is_none_since_stats_always_empty(self, chat_completion_response):
        metrics = LMStudioClient._extract_metrics(
            chat_completion_response, "test-model", 1000.0
        )
        assert metrics.time_to_first_token_ms is None

    def test_total_duration_ms_is_recorded(self, chat_completion_response):
        metrics = LMStudioClient._extract_metrics(
            chat_completion_response, "test-model", 1234.5
        )
        assert metrics.total_duration_ms == pytest.approx(1234.5)

    def test_token_counts_extracted(self, chat_completion_response):
        metrics = LMStudioClient._extract_metrics(
            chat_completion_response, "test-model", 1000.0
        )
        assert metrics.prompt_tokens == 12
        assert metrics.completion_tokens == 8
