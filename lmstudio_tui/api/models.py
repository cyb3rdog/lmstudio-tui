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
        if isinstance(v, str):
            return v
        return str(v) if v is not None else ""

    @field_validator("quantization", mode="before")
    @classmethod
    def _coerce_quantization(cls, v: object) -> str | None:
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
        """Accept unknown state strings gracefully.

        Uses .value to avoid Python 3.11 str(StrEnum) → 'Class.NAME' behaviour.
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
        return self.instance_id is not None or self.state == ModelState.LOADED


class ModelsResponse(BaseModel):
    """Accepts both LM Studio ({"models": [...]}) and OpenAI ({"data": [...]}) schemas."""

    models: list[ModelInfo] = Field(default_factory=list)
    data: list[ModelInfo] = Field(default_factory=list)

    @property
    def model_list(self) -> list[ModelInfo]:
        return self.models or self.data

    @classmethod
    def from_raw(cls, raw: dict) -> "ModelsResponse":
        def _extract_instance_id(m: dict) -> str | None:
            li = m.get("loaded_instances", [])
            return li[0].get("id") if li else None

        def _normalize(m: dict) -> dict:
            return {
                **m,
                "id": m.get("key") or m.get("id", ""),
                "instance_id": _extract_instance_id(m),
                "quantization": m.get("quantization"),
            }

        if "models" in raw:
            return cls(models=[_normalize(m) for m in raw["models"]])
        elif "data" in raw:
            return cls(data=raw["data"])
        return cls()


class LoadRequest(BaseModel):
    model: str
    gpu_layers: int | None = None
    context_length: int | None = None


class LoadResponse(BaseModel):
    instance_id: str
    model: str = ""
    type: str = "llm"
    load_time_seconds: float = 0.0
    status: str = ""


class UnloadRequest(BaseModel):
    instance_id: str


class DownloadStatus(BaseModel):
    model: str = ""
    status: str = ""
    progress: float = 0.0
    bytes_downloaded: int | None = None
    bytes_total: int | None = None


class ChatMessage(BaseModel):
    role: str
    content: str | list[Any]
    tool_call_id: str | None = None
    tool_calls: list[Any] | None = None


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    stream: bool = False
    max_tokens: int | None = None
    temperature: float = 0.0
    top_p: float | None = None
    repeat_penalty: float | None = None
    # Tool calling
    tools: list[dict] | None = None
    tool_choice: str | dict | None = None


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
    """Performance metrics from a single inference call.

    All timing fields are wall-clock measurements (LM Studio's stats{} is always empty).
    Fields added for agentic benchmarking are optional and default to neutral values.
    """

    model_id: str = ""
    # Throughput
    tokens_per_second: float | None = None
    time_to_first_token_ms: float | None = None   # requires streaming
    tpot_ms: float | None = None                   # time-per-output-token (streaming)
    total_duration_ms: float | None = None
    # Token counts
    prompt_tokens: int = 0
    completion_tokens: int = 0
    reasoning_tokens: int = 0                      # from reasoning_content field
    # Tool calling (populated only in tool mode)
    tool_called: bool = False
    tool_name_correct: bool | None = None          # None = not evaluated
    tool_args_score: float | None = None           # 0.0–1.0 fuzzy match
    # Load time (populated only in load mode)
    load_time_ms: float | None = None
    was_jit: bool = False                          # first run detected JIT load
