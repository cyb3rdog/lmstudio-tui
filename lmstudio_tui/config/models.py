from __future__ import annotations

from dataclasses import dataclass, field

from ..constants import DEFAULT_REQUEST_TIMEOUT_S, METRICS_WINDOW, MIN_POLL_INTERVAL_S


@dataclass
class ModelPref:
    """Remembered load parameters for a specific model."""
    gpu_layers: int | None = None
    context_length: int | None = None


@dataclass
class ServerConfig:
    name: str = "default"
    endpoint: str = "http://localhost:1234"
    api_key: str = ""
    # Per-server HTTP request timeout in seconds. Large models (70B+ Q4+)
    # can take 600–900s to JIT-load. Falls back to DEFAULT_REQUEST_TIMEOUT_S.
    timeout_s: float = DEFAULT_REQUEST_TIMEOUT_S

    def headers(self) -> dict[str, str]:
        if self.api_key:
            return {"Authorization": f"Bearer {self.api_key}"}
        return {}


@dataclass
class BenchmarkConfig:
    default_prompt_set: str = "mixed"
    default_samples: int = 10
    warmup_runs: int = 2
    export_dir: str = "~/.lmstudio-tui/benchmarks"


@dataclass
class UIConfig:
    poll_interval_s: float = 3.0
    theme: str = "textual-dark"


@dataclass
class AppConfig:
    servers: list[ServerConfig] = field(default_factory=lambda: [ServerConfig()])
    active_server: str = "default"
    benchmark: BenchmarkConfig = field(default_factory=BenchmarkConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    model_prefs: dict[str, ModelPref] = field(default_factory=dict)
    # Metrics ring-buffer window size (samples retained per model).
    # On constrained hardware (Pi Zero 2W) reduce from default 120.
    metrics_window: int = METRICS_WINDOW

    @property
    def active_server_config(self) -> ServerConfig:
        for s in self.servers:
            if s.name == self.active_server:
                return s
        return self.servers[0] if self.servers else ServerConfig()

    def validate(self) -> None:
        """Clamp and warn on out-of-range values. Called at load time."""
        if self.ui.poll_interval_s < MIN_POLL_INTERVAL_S:
            self.ui.poll_interval_s = MIN_POLL_INTERVAL_S
        if self.metrics_window < 10:
            self.metrics_window = 10
        elif self.metrics_window > 500:
            self.metrics_window = 500
        for s in self.servers:
            if s.timeout_s < 10.0:
                s.timeout_s = 10.0
            elif s.timeout_s > 3600.0:
                s.timeout_s = 3600.0