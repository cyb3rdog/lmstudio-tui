from __future__ import annotations

import pytest


# ── Shared LM Studio API response fixtures ────────────────────────────────────

@pytest.fixture
def lmstudio_models_response():
    """Realistic GET /api/v1/models response from LM Studio v1."""
    return {
        "models": [
            {
                "key": "llama-3-8b-instruct-q4_K_M",
                "object": "model",
                "quantization": {"name": "Q4_K_M", "bits": 4},
                "max_context_length": 8192,
                "loaded_instances": [
                    {"id": "llama-3-8b-instruct-q4_K_M:0", "model": "llama-3-8b-instruct-q4_K_M"}
                ],
                "state": "loaded",
            },
            {
                "key": "mistral-7b-instruct-q8_0",
                "object": "model",
                "quantization": {"name": "Q8_0", "bits": 8},
                "max_context_length": 32768,
                "loaded_instances": [],
                "state": "not_loaded",
            },
            {
                "key": "phi-3-mini-4k-instruct-q4",
                "object": "model",
                "quantization": None,
                "max_context_length": 4096,
                "loaded_instances": [],
                "state": "not_loaded",
            },
        ]
    }


@pytest.fixture
def openai_models_response():
    """OpenAI-compatible GET /v1/models response."""
    return {
        "object": "list",
        "data": [
            {"id": "gpt-4", "object": "model", "owned_by": "openai"},
            {"id": "gpt-3.5-turbo", "object": "model", "owned_by": "openai"},
        ],
    }


@pytest.fixture
def chat_completion_response():
    """Non-streaming chat completion response."""
    return {
        "id": "chatcmpl-abc123",
        "object": "chat.completion",
        "model": "llama-3-8b-instruct-q4_K_M",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Hello! How can I help?"},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 12,
            "completion_tokens": 8,
            "total_tokens": 20,
        },
        "stats": {},
    }
