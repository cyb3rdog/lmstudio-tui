from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ModelState(str, Enum):
    LOADED = "loaded"
    NOT_LOADED = "not_loaded"
    LOADING = "loading"


class ModelInfo(BaseModel):
    """Model info parsed from LM Studio /api/v1/models.

    API field          →  ModelInfo field
    ─────────────────────────────────────
    key                →  id
    models[*].loaded_instances[0].id  →  instance_id
    quantization.name  →  quantization (str)
    max_context_length (top-level)    →  max_context_length
    gpu_layers         →  (not in LM Studio v1 API — always None)
    kv_cache_type      →  (not in LM Studio v1 API — always None)
    """

    model_config = ConfigDict(extra="ignore")

    id: str = ""
    object: str = "model"
    owned_by: str = ""
    # LM Studio v1 extras
    state: ModelState | None = None
    max_context_length: int | None = None
    quantization: str | None = None
    instance_id: str | None = None
    # Load configuration — NOT returned by LM Studio v1 /api/v1/models
    # These stay None; they are populated from load_model response when needed.
    gpu_layers: int | None = None
    context_length: int | None = None
    kv_cache_type: str | None = None
    # Inference parameters — NOT returned by LM Studio v1 /api/v1/models
    temperature: float | None = None
    top_p: float | None = None
    repeat_penalty: float | None = None

    @field_validator("id", mode="before")
    @classmethod
    def _coerce_id(cls, v: object) -> str:
        """Accept 'key' (LM Studio) or 'id' (OpenAI)."""
        if isinstance(v, str):
            return v
        return str(v) if v is not None else ""

    @field_validator("quantization", mode="before")
    @classmethod
    def _coerce_quantization(cls, v: object) -> str | None:
        """Accept quantization.name (LM Studio dict) or a plain str."""
        if v is None:
            return None
        if isinstance(v, str):
            return v
        if isinstance(v, dict):
            return v.get("name")
        return str(v)

    @field_validator("state", mode="before")
    @classmethod
    def _coerce_state(cls, v: object) -> object:
        """Accept unknown state strings gracefully instead of crashing.

        Handles str, ModelState enum, and None.  Uses .value to avoid the
        Python 3.11 behaviour where str(StrEnum.member) returns 'Class.NAME'
        rather than the underlying string value.
        """
        if v is None:
            return None
        if isinstance(v, ModelState):
            return v
        raw = v.value if hasattr(v, "value") else str(v)
        try:
            return ModelState(raw.lower())
        except ValueError:
            return None

    @property
    def is_loaded(self) -> bool:
        """True when the model has at least one loaded instance."""
        return self.instance_id is not None or self.state == ModelState.LOADED


class ModelsResponse(BaseModel):
    """Accepts both the LM Studio schema ({"models": [...]}) and the
    OpenAI-compatible schema ({"data": [...]})."""

    # At least one of these will be populated; use whichever the server sent.
    models: list[ModelInfo] = Field(default_factory=list)
    data: list[ModelInfo] = Field(default_factory=list)

    @property
    def model_list(self) -> list[ModelInfo]:
        return self.models or self.data

    @classmethod
    def from_raw(cls, raw: dict) -> "ModelsResponse":
        """Parse raw server JSON, handling the 'models' (LM Studio) or 'data'
        (OpenAI) top-level key, and extracting instance_ids from the nested
        loaded_instances array."""

        def _extract_instance_id(m: dict) -> str | None:
            li = m.get("loaded_instances", [])
            return li[0].get("id") if li else None

        def _normalize(m: dict) -> dict:
            """Flatten LM Studio-specific fields so Pydantic can validate them."""
            instance_id = _extract_instance_id(m)
            return {
                **m,
                "id": m.get("key") or m.get("id", ""),
                "instance_id": instance_id,
                "quantization": m.get("quantization"),
            }

        if "models" in raw:
            normalized = [_normalize(m) for m in raw["models"]]
            return cls(models=normalized)
        elif "data" in raw:
            return cls(data=raw["data"])
        else:
            # Empty or malformed — return empty list
            return cls()


class LoadRequest(BaseModel):
    model: str
    gpu_layers: int | None = None
    context_length: int | None = None


class LoadResponse(BaseModel):
    """Response from POST /api/v1/models/load."""

    instance_id: str
    model: str = ""          # may be omitted by server
    type: str = "llm"       # may be omitted
    load_time_seconds: float = 0.0   # informational only
    status: str = ""         # "loaded" — informational only


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
