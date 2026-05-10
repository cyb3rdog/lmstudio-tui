from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import ContentSwitcher, Footer, Header, Label, ListItem, ListView

from .config.loader import config_exists, create_default_config, load_config
from .config.models import AppConfig
from .screens.benchmark_runner import BenchmarkRunner
from .screens.dashboard import Dashboard
from .screens.live_monitor import LiveMonitor
from .screens.model_manager import ModelManager
from .screens.settings import Settings
from .state.metrics_store import MetricsStore
from .state.server_registry import ServerRegistry

_NAV_ITEMS = [
    ("dashboard",  "  Dashboard"),
    ("models",     "  Models"),
    ("monitor",    "  Monitor"),
    ("benchmark",  "  Benchmark"),
    ("settings",   "  Settings"),
]


class LMStudioApp(App[None]):
    TITLE = "LM Studio TUI"
    CSS_PATH = "app.tcss"

    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+r", "force_refresh", "Refresh"),
    ]

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self.config = config
        self.server_registry = ServerRegistry(config.servers)
        self.metrics_store = MetricsStore()

    # ── layout ────────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main-layout"):
            with Vertical(id="sidebar"):
                yield Label("  LM Studio TUI", id="sidebar-title")
                yield ListView(
                    *[ListItem(Label(label), name=key) for key, label in _NAV_ITEMS],
                    id="nav-list",
                )
            with ContentSwitcher(initial="dashboard", id="content-area"):
                yield Dashboard(id="dashboard")
                yield ModelManager(id="models")
                yield LiveMonitor(id="monitor")
                yield BenchmarkRunner(id="benchmark")
                yield Settings(id="settings")
        yield Footer()

    # ── lifecycle ─────────────────────────────────────────────────────────────

    async def on_mount(self) -> None:
        # Highlight first nav item
        nav = self.query_one("#nav-list", ListView)
        nav.focus()
        nav.index = 0

        # Connect to configured servers in background
        for server in self.config.servers:
            self.run_worker(self.server_registry.connect(server.name), exclusive=False)

    async def on_unmount(self) -> None:
        await self.server_registry.disconnect_all()

    # ── navigation ────────────────────────────────────────────────────────────

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.list_view.id == "nav-list" and event.item.name:
            self.query_one("#content-area", ContentSwitcher).current = event.item.name

    def action_force_refresh(self) -> None:
        for server in self.config.servers:
            self.run_worker(self.server_registry.connect(server.name), exclusive=False)


# ── factory ───────────────────────────────────────────────────────────────────

async def _run_onboarding() -> AppConfig:
    """Run onboarding modal inside a temporary headless app, return config."""
    from .screens.modals.onboarding import OnboardingModal

    class _OnboardingApp(App[AppConfig]):
        def compose(self) -> ComposeResult:
            yield Label("")

        async def on_mount(self) -> None:
            result = await self.push_screen_wait(OnboardingModal())
            config = create_default_config(result.endpoint, result.api_key)
            self.exit(config)

    app = _OnboardingApp()
    return await app.run_async()


def create_app(endpoint: str | None = None, api_key: str | None = None) -> LMStudioApp:
    if not config_exists():
        if endpoint:
            config = create_default_config(endpoint, api_key or "")
        else:
            # Will trigger onboarding on first launch
            from .config.models import AppConfig, ServerConfig
            config = AppConfig(servers=[ServerConfig(endpoint=endpoint or "http://localhost:1234")])
    else:
        config = load_config()

    if endpoint:
        # CLI override: patch the active server's endpoint at runtime
        config.active_server_config.endpoint = endpoint
        if api_key is not None:
            config.active_server_config.api_key = api_key

    return LMStudioApp(config)
