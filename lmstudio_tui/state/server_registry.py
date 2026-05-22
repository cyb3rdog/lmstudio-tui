from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum

from textual.app import App

from ..api import exceptions as exc
from ..api.client import LMStudioClient
from ..api.models import ModelInfo
from ..config.models import ServerConfig


class ConnectionState(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class ServerConnection:
    config: ServerConfig
    client: LMStudioClient | None = None
    state: ConnectionState = ConnectionState.DISCONNECTED
    ping_ms: float | None = None
    last_error: str | None = None
    models: list[ModelInfo] = field(default_factory=list)


class ServerRegistry:
    """Manages LMStudioClient connections.

    Single-server for v1; the list[ServerConnection] structure allows
    adding multi-server switching later with minimal refactoring.
    """

    def __init__(self, configs: list[ServerConfig], active_server: str = "") -> None:
        self._connections: dict[str, ServerConnection] = {
            c.name: ServerConnection(config=c) for c in configs
        }
        # Use provided active_server, or fall back to first server name
        self._active: str = active_server or (configs[0].name if configs else "")
        # Per-server locks prevent concurrent connect() calls racing on the same server.
        self._connect_locks: dict[str, asyncio.Lock] = {}

    @property
    def active_name(self) -> str:
        return self._active

    @active_name.setter
    def active_name(self, name: str) -> None:
        if name in self._connections:
            self._active = name

    @property
    def active_connection(self) -> ServerConnection | None:
        return self._connections.get(self._active)

    @property
    def active_client(self) -> LMStudioClient | None:
        conn = self.active_connection
        return conn.client if conn else None

    def get_connection(self, name: str) -> ServerConnection | None:
        return self._connections.get(name)

    def all_connections(self) -> list[ServerConnection]:
        return list(self._connections.values())

    def add_server(self, config: ServerConfig) -> None:
        self._connections[config.name] = ServerConnection(config=config)

    async def wait_for_client(self, timeout_s: float = 5.0) -> LMStudioClient | None:
        """Poll active_client until connected or timeout.

        Replaces copy-pasted busy-wait loops across screens.
        Returns the client if available, or None on timeout.
        """
        deadline = asyncio.get_running_loop().time() + timeout_s
        while True:
            client = self.active_client
            if client is not None:
                return client
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                return None
            await asyncio.sleep(min(0.25, remaining))

    def remove_server(self, name: str) -> None:
        self._connections.pop(name, None)
        if self._active == name:
            self._active = next(iter(self._connections)) if self._connections else ""

    async def connect(self, name: str) -> None:
        conn = self._connections.get(name)
        if not conn:
            return

        # Serialize per-server connects so concurrent callers (Ctrl+R spam,
        # on_mount + force_refresh) don't race and close each other's clients.
        if name not in self._connect_locks:
            self._connect_locks[name] = asyncio.Lock()
        async with self._connect_locks[name]:
            await self._connect_locked(name, conn)

    async def _connect_locked(self, name: str, conn: ServerConnection) -> None:
        # Close any existing client before creating a new one.
        # Failing to do this leaks the underlying httpx connection pool and
        # its file descriptors — repeated reconnects (Ctrl+R, error recovery)
        # exhaust the OS fd limit and crash the process.
        if conn.client:
            try:
                await conn.client.close()
            except Exception:
                pass
            conn.client = None

        conn.state = ConnectionState.CONNECTING
        conn.last_error = None
        client: LMStudioClient | None = None
        try:
            client = LMStudioClient(conn.config)
            try:
                models = await client.list_models()
                conn.models = models
            except exc.AuthError:
                raise
            except exc.APIError:
                pass
            ping = await client.ping()
            conn.client = client
            conn.ping_ms = ping
            conn.state = ConnectionState.CONNECTED
        except exc.AuthError:
            conn.state = ConnectionState.ERROR
            conn.last_error = "Auth failed: check API key in Settings"
            if client:
                await client.close()
        except Exception as e:
            conn.state = ConnectionState.ERROR
            conn.last_error = str(e)
            if client:
                await client.close()

    async def connect_all(self) -> None:
        for name in self._connections:
            await self.connect(name)

    async def disconnect_all(self) -> None:
        # Snapshot server names before closing (needed for metrics cleanup below).
        server_names = list(self._connections.keys())
        for conn in self._connections.values():
            if conn.client:
                await conn.client.close()
                conn.client = None
                conn.state = ConnectionState.DISCONNECTED
        # Evict stale metrics for all servers on disconnect.
        # If an app reference was injected via attach_app(), clear metrics here.
        # Safe to call even if app or metrics_store is None — MetricsStore.clear_server()
        # handles empty state gracefully.
        app = getattr(self, "app", None)
        if app is not None:
            store = getattr(app, "metrics_store", None)
            if store is not None:
                for name in server_names:
                    store.clear_server(name)

    def attach_app(self, app: App) -> None:
        """Inject the parent App reference for cross-cutting shutdown cleanup.

        Called by App.__init__() after ServerRegistry is constructed.
        Required for disconnect_all() to evict stale metrics on shutdown.
        """
        self.app = app
