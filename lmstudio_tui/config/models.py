from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ServerConfig:
    name: str = "default"
    endpoint: str = "http://localhost:1234"
    api_key: str = ""

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

    @property
    def active_server_config(self) -> ServerConfig:
        for s in self.servers:
            if s.name == self.active_server:
                return s
        return self.servers[0] if self.servers else ServerConfig()
