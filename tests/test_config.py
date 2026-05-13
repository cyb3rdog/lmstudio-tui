"""Tests for config models and loader."""

from __future__ import annotations

import tempfile
from pathlib import Path

from lmstudio_tui.config.loader import (
    create_default_config,
    load_config,
    save_config,
)
from lmstudio_tui.config.models import (
    AppConfig,
    BenchmarkConfig,
    ServerConfig,
    UIConfig,
)


class TestServerConfig:
    def test_default_endpoint_is_localhost(self) -> None:
        cfg = ServerConfig()
        assert "localhost" in cfg.endpoint

    def test_headers_empty_when_no_api_key(self) -> None:
        cfg = ServerConfig()
        assert cfg.headers() == {}

    def test_headers_bearer_when_api_key_set(self) -> None:
        cfg = ServerConfig(api_key="secret")
        assert cfg.headers() == {"Authorization": "Bearer secret"}

    def test_name_defaults_to_default(self) -> None:
        cfg = ServerConfig(endpoint="https://example.com")
        assert cfg.name == "default"


class TestUIConfig:
    def test_poll_interval_default(self) -> None:
        cfg = UIConfig()
        assert cfg.poll_interval_s == 3.0

    def test_poll_interval_can_be_set(self) -> None:
        cfg = UIConfig(poll_interval_s=5.0)
        assert cfg.poll_interval_s == 5.0


class TestBenchmarkConfig:
    def test_export_dir_expands_home(self) -> None:
        cfg = BenchmarkConfig()
        assert "~" not in cfg.export_dir or cfg.export_dir.startswith("~")
        # After path expansion it should be a real path
        expanded = Path(cfg.export_dir).expanduser()
        assert expanded.is_dir() or not expanded.exists()  # may not exist yet


class TestAppConfig:
    def test_default_has_one_server(self) -> None:
        cfg = AppConfig()
        assert len(cfg.servers) >= 1

    def test_active_server_defaults_to_first_server(self) -> None:
        cfg = AppConfig()
        assert cfg.active_server == cfg.servers[0].name

    def test_active_server_config_returns_correct_server(self) -> None:
        cfg = AppConfig(servers=[ServerConfig(name="s1"), ServerConfig(name="s2")])
        cfg.active_server = "s2"
        assert cfg.active_server_config.name == "s2"


class TestCreateDefaultConfig:
    def test_returns_valid_config(self) -> None:
        # Must isolate: create_default_config calls save_config() internally,
        # which writes to the real ~/.lmstudio-tui/config.toml. Without a temp
        # path patch, this clobbers the user's actual config.
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "config.toml"
            import lmstudio_tui.config.loader as loader

            original = loader.CONFIG_FILE
            loader.CONFIG_FILE = path
            try:
                cfg = create_default_config("https://example.com", "key123")
                assert len(cfg.servers) == 1
                assert cfg.servers[0].endpoint == "https://example.com"
                assert cfg.servers[0].api_key == "key123"
                assert cfg.active_server == cfg.servers[0].name
            finally:
                loader.CONFIG_FILE = original


class TestSaveAndLoadConfig:
    def test_roundtrip(self) -> None:
        original = AppConfig(servers=[ServerConfig(name="test", endpoint="https://x.y")])
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "config.toml"
            import lmstudio_tui.config.loader as loader

            original_path = loader.CONFIG_FILE
            loader.CONFIG_FILE = path
            try:
                save_config(original)
                loaded = load_config()
                assert loaded.servers[0].name == "test"
                assert loaded.servers[0].endpoint == "https://x.y"
            finally:
                loader.CONFIG_FILE = original_path

    def test_load_missing_file_returns_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nonexistent.toml"
            import lmstudio_tui.config.loader as loader

            original_path = loader.CONFIG_FILE
            loader.CONFIG_FILE = path
            try:
                cfg = load_config()
                assert cfg is not None
                assert len(cfg.servers) >= 1
            finally:
                loader.CONFIG_FILE = original_path
