"""Tests for server_registry: connect/disconnect lifecycle and app attachment."""

from __future__ import annotations

import pytest

from lmstudio_tui.config.models import ServerConfig
from lmstudio_tui.state.server_registry import (
    ConnectionState,
    ServerConnection,
    ServerRegistry,
)


class TestServerRegistryInit:
    def test_creates_one_connection_per_config(self) -> None:
        cfg = [ServerConfig(name="s1"), ServerConfig(name="s2")]
        reg = ServerRegistry(cfg)
        assert set(reg._connections.keys()) == {"s1", "s2"}

    def test_active_defaults_to_first_server(self) -> None:
        cfg = [ServerConfig(name="first"), ServerConfig(name="second")]
        reg = ServerRegistry(cfg)
        assert reg.active_name == "first"

    def test_active_derived_from_explicit_arg(self) -> None:
        cfg = [ServerConfig(name="first"), ServerConfig(name="second")]
        reg = ServerRegistry(cfg, active_server="second")
        assert reg.active_name == "second"

    def test_active_derived_from_empty_list(self) -> None:
        reg = ServerRegistry([])
        assert reg.active_name == ""

    def test_active_connection_returns_correct_connection(self) -> None:
        cfg = [ServerConfig(name="s1"), ServerConfig(name="s2")]
        reg = ServerRegistry(cfg, active_server="s2")
        conn = reg.active_connection
        assert conn is not None
        assert conn.config.name == "s2"

    def test_active_connection_none_for_missing_server(self) -> None:
        reg = ServerRegistry([ServerConfig(name="s1")], active_server="nonexistent")
        assert reg.active_connection is None

    def test_active_client_returns_none_when_not_connected(self) -> None:
        reg = ServerRegistry([ServerConfig(name="s1")])
        assert reg.active_client is None


class TestServerRegistryAddRemove:
    def test_add_server_inserts_new_connection(self) -> None:
        reg = ServerRegistry([ServerConfig(name="s1")])
        reg.add_server(ServerConfig(name="s2"))
        assert "s2" in reg._connections
        assert reg.active_name == "s1"  # active unchanged

    def test_remove_server_deletes_connection(self) -> None:
        reg = ServerRegistry([ServerConfig(name="s1"), ServerConfig(name="s2")])
        reg.remove_server("s1")
        assert "s1" not in reg._connections
        assert "s2" in reg._connections

    def test_remove_active_server_reassigns_active(self) -> None:
        reg = ServerRegistry(
            [ServerConfig(name="s1"), ServerConfig(name="s2")],
            active_server="s1",
        )
        reg.remove_server("s1")
        assert reg.active_name == "s2"

    def test_remove_last_server_clears_active(self) -> None:
        reg = ServerRegistry([ServerConfig(name="s1")], active_server="s1")
        reg.remove_server("s1")
        assert reg.active_name == ""

    def test_remove_nonexistent_server_noops(self) -> None:
        reg = ServerRegistry([ServerConfig(name="s1")])
        reg.remove_server("nonexistent")  # must not raise
        assert list(reg._connections.keys()) == ["s1"]


class TestServerRegistryActiveNameSetter:
    def test_set_active_name_switches_connection(self) -> None:
        reg = ServerRegistry(
            [ServerConfig(name="s1"), ServerConfig(name="s2")]
        )
        reg.active_name = "s2"
        assert reg.active_name == "s2"
        assert reg.active_connection.config.name == "s2"

    def test_set_active_name_to_nonexistent_ignored(self) -> None:
        reg = ServerRegistry([ServerConfig(name="s1")])
        reg.active_name = "nonexistent"
        assert reg.active_name == "s1"  # unchanged


class TestServerRegistryAttachApp:
    def test_attach_app_stores_reference(self) -> None:
        reg = ServerRegistry([ServerConfig(name="s1")])
        fake_app = object()
        reg.attach_app(fake_app)
        assert reg.app is fake_app

    def test_disconnect_all_without_app_attached_does_not_raise(self) -> None:
        # Regression: prior version accessed self.app.metrics_store directly,
        # crashing when app was never injected. Now uses getattr() guard.
        reg = ServerRegistry([ServerConfig(name="s1")])
        # No attach_app() call — must not raise AttributeError
        import asyncio
        asyncio.get_event_loop().run_until_complete(reg.disconnect_all())

    def test_disconnect_all_clears_all_clients(self) -> None:
        # Verify disconnect_all iterates all connections (not just active)
        cfg1 = ServerConfig(name="s1")
        cfg2 = ServerConfig(name="s2")
        reg = ServerRegistry([cfg1, cfg2])

        # Create a mock client with a close() method
        class MockClient:
            def __init__(self) -> None:
                self.closed = False

            async def close(self) -> None:
                self.closed = True

        client1 = MockClient()
        client2 = MockClient()
        reg._connections["s1"].client = client1
        reg._connections["s2"].client = client2

        # Mock app with metrics_store so the clear_server guard passes
        class MockMetricsStore:
            def __init__(self) -> None:
                self.cleared: list[str] = []

            def clear_server(self, name: str) -> None:
                self.cleared.append(name)

        class MockApp:
            def __init__(self) -> None:
                self.metrics_store = MockMetricsStore()

        mock_app = MockApp()
        reg.attach_app(mock_app)
        import asyncio
        asyncio.get_event_loop().run_until_complete(reg.disconnect_all())

        assert client1.closed is True
        assert client2.closed is True
        assert "s1" in mock_app.metrics_store.cleared
        assert "s2" in mock_app.metrics_store.cleared


class TestServerRegistryAllConnections:
    def test_all_connections_returns_all(self) -> None:
        cfg = [ServerConfig(name="s1"), ServerConfig(name="s2")]
        reg = ServerRegistry(cfg)
        all_conns = reg.all_connections()
        assert len(all_conns) == 2
        names = {c.config.name for c in all_conns}
        assert names == {"s1", "s2"}

    def test_get_connection_returns_correct(self) -> None:
        reg = ServerRegistry([ServerConfig(name="s1"), ServerConfig(name="s2")])
        conn = reg.get_connection("s2")
        assert conn is not None
        assert conn.config.name == "s2"

    def test_get_connection_missing_returns_none(self) -> None:
        reg = ServerRegistry([ServerConfig(name="s1")])
        assert reg.get_connection("nonexistent") is None


class TestServerConnectionDataclass:
    def test_default_state_is_disconnected(self) -> None:
        conn = ServerConnection(config=ServerConfig())
        assert conn.state == ConnectionState.DISCONNECTED
        assert conn.client is None
        assert conn.ping_ms is None
        assert conn.last_error is None
