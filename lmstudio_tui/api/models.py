from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ModelState(str, Enum):
    LOADED = "loaded"
    NOT_LOADED = "not_loaded"
    LOADING = "loading"


class ModelInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    object: str = "model"
    owned_by: str = ""
    # LM Studio v1 extras
    state: ModelState | None = None
    max_context_length: int | None = None
    quantization: str | None = None
    instance_id: str | None = None
    # Load configuration (present when loaded)
    gpu_layers: int | None = None
    context_length: int | None = None
    kv_cache_type: str | None = None
    # Inference parameters (returned by LM Studio when model is loaded)
    temperature: float | None = None
    top_p: float | None = None
    repeat_penalty: float | None = None

    @field_validator("state", mode="before")
    @classmethod
    def _coerce_state(cls, v: object) -> object:
        """Accept unknown state strings gracefully instead of crashing."""
        if v is None:
            return None
        try:
            return ModelState(str(v).lower())
        except ValueError:
            return None

    @property
    def is_loaded(self) -> bool:
        if self.state is not None:
            return self.state == ModelState.LOADED
        # Fallback: if state is absent but instance_id is present, model is loaded
        return self.instance_id is not None


class ModelsResponse(BaseModel):
    object: str = "list"
    data: list[ModelInfo] = Field(default_factory=list)


class LoadRequest(BaseModel):
    model: str
    gpu_layers: int | None = None
    context_length: int | None = None


class LoadResponse(BaseModel):
    instance_id: str
    model: str


class UnloadRequest(BaseModel):
    instance_id: str


class DownloadStatus(BaseModel):
    model: str = ""
    status: str = ""        # "downloading" | "complete" | "error"
    progress: float = 0.0   # 0.0 – 1.0
    bytes_downloaded: int | None = None
    bytes_total: int | None = None


class ChatMessage(BaseModel):
    role: str
    content: str | list[Any]


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    stream: bool = False
    max_tokens: int | None = None
    temperature: float = 0.0
    top_p: float | None = None
    repeat_penalty: float | None = None


class CompletionRequest(BaseModel):
    model: str
    prompt: str
    stream: bool = False
    max_tokens: int | None = None
    temperature: float = 0.0


class UsageStats(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class CompletionMetrics(BaseModel):
    """Performance metrics from a single inference call."""
    model_id: str = ""
    tokens_per_second: float | None = None
    time_to_first_token_ms: float | None = None
    total_duration_ms: float | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
