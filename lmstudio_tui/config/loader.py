from __future__ import annotations

import tomllib
from pathlib import Path

import tomli_w

from .defaults import DEFAULT_CONFIG_TOML
from .models import AppConfig, BenchmarkConfig, ServerConfig, UIConfig

CONFIG_DIR = Path.home() / ".lmstudio-tui"
CONFIG_FILE = CONFIG_DIR / "config.toml"


def config_exists() -> bool:
    return CONFIG_FILE.exists()


def load_config() -> AppConfig:
    if not CONFIG_FILE.exists():
        return AppConfig()

    with open(CONFIG_FILE, "rb") as f:
        data = tomllib.load(f)

    servers = [
        ServerConfig(
            name=s.get("name", "default"),
            endpoint=s.get("endpoint", "http://localhost:1234"),
            api_key=s.get("api_key", ""),
        )
        for s in data.get("servers", [])
    ]
    if not servers:
        servers = [ServerConfig()]

    bdata = data.get("benchmark", {})
    bench = BenchmarkConfig(
        default_prompt_set=bdata.get("default_prompt_set", "mixed"),
        default_samples=bdata.get("default_samples", 10),
        warmup_runs=bdata.get("warmup_runs", 2),
        export_dir=bdata.get("export_dir", "~/.lmstudio-tui/benchmarks"),
    )

    udata = data.get("ui", {})
    ui = UIConfig(
        poll_interval_s=udata.get("poll_interval_s", 3.0),
        theme=udata.get("theme", "textual-dark"),
    )

    return AppConfig(
        servers=servers,
        active_server=data.get("active_server", servers[0].name),
        benchmark=bench,
        ui=ui,
    )


def save_config(config: AppConfig) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    data: dict = {
        "active_server": config.active_server,
        "servers": [
            {"name": s.name, "endpoint": s.endpoint, "api_key": s.api_key}
            for s in config.servers
        ],
        "benchmark": {
            "default_prompt_set": config.benchmark.default_prompt_set,
            "default_samples": config.benchmark.default_samples,
            "warmup_runs": config.benchmark.warmup_runs,
            "export_dir": config.benchmark.export_dir,
        },
        "ui": {
            "poll_interval_s": config.ui.poll_interval_s,
            "theme": config.ui.theme,
        },
    }

    with open(CONFIG_FILE, "wb") as f:
        tomli_w.dump(data, f)


def create_default_config(endpoint: str, api_key: str) -> AppConfig:
    server = ServerConfig(name="default", endpoint=endpoint, api_key=api_key)
    config = AppConfig(servers=[server], active_server="default")
    save_config(config)
    return config
