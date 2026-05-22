from __future__ import annotations

import logging

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import ContentSwitcher, Footer, Header, Tab, Tabs

from .config.loader import config_exists, create_default_config, load_config, save_config
from .config.models import AppConfig, ServerConfig
from .screens.benchmark_runner import BenchmarkRunner
from .screens.chat import ChatScreen
from .screens.dashboard import Dashboard
from .screens.download_manager import DownloadManager
from .screens.live_monitor import LiveMonitor
from .screens.model_manager import ModelManager
from .screens.settings import Settings
from .state.metrics_store import MetricsStore
from .state.server_registry import ServerRegistry

_logger = logging.getLogger("lmstudio_tui.app")

# (key, label, shortcut-hint)
_NAV_ITEMS = [
    ("dashboard",  "Dashboard",  "1"),
    ("models",     "Models",     "2"),
    ("chat",       "Chat",       "3"),
    ("monitor",    "Monitor",    "4"),
    ("benchmark",  "Benchmark",  "5"),
    ("downloads",  "Downloads",  "6"),
    ("settings",   "Settings",   "7"),
]


class LMStudioApp(App[None]):
    TITLE = "LM Studio TUI"
    CSS_PATH = "app.tcss"

    BINDINGS = [
        Binding("ctrl+q",        "quit",            "Quit",      show=True),
        Binding("question_mark", "show_shortcuts",  "?",         show=True),
        Binding("ctrl+r",        "force_refresh",   "Refresh",   show=False),
        Binding("1", "goto('dashboard')",  "Dashboard",  show=False),
        Binding("2", "goto('models')",     "Models",     show=False),
        Binding("3", "goto('chat')",       "Chat",       show=False),
        Binding("4", "goto('monitor')",    "Monitor",    show=False),
        Binding("5", "goto('benchmark')",  "Benchmark",  show=False),
        Binding("6", "goto('downloads')",  "Downloads",  show=False),
        Binding("7", "goto('settings')",   "Settings",   show=False),
    ]

    def __init__(self, config: AppConfig, needs_onboarding: bool = False) -> None:
        super().__init__()
        self.config = config
        self.server_registry = ServerRegistry(config.servers, active_server=config.active_server)
        self.server_registry.attach_app(self)
        self.metrics_store = MetricsStore(window=config.metrics_window)
        self._needs_onboarding = needs_onboarding
        self._current_screen = "dashboard"

    # ── layout ────────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header()
        yield Tabs(
            *[Tab(f"[{hint}] {label}", id=key) for key, label, hint in _NAV_ITEMS],
            id="nav-tabs",
        )
        with ContentSwitcher(initial="dashboard", id="content-area"):
            yield Dashboard(id="dashboard")
            yield ModelManager(id="models")
            yield ChatScreen(id="chat")
            yield LiveMonitor(id="monitor")
            yield BenchmarkRunner(id="benchmark")
            yield DownloadManager(id="downloads")
            yield Settings(id="settings")
        yield Footer()

    # ── lifecycle ─────────────────────────────────────────────────────────────

    async def on_mount(self) -> None:
        if self._needs_onboarding:
            self.run_worker(self._run_onboarding(), exclusive=True)
        else:
            for server in self.config.servers:
                self.run_worker(self.server_registry.connect(server.name), exclusive=False)

    async def _run_onboarding(self) -> None:
        from .screens.modals.onboarding import OnboardingModal
        server_cfg = await self.push_screen_wait(OnboardingModal())
        if server_cfg is not None:
            self.config.servers = [server_cfg]
            self.config.active_server = server_cfg.name
            save_config(self.config)
            self.server_registry = ServerRegistry(self.config.servers, active_server=server_cfg.name)
            self.server_registry.attach_app(self)
        else:
            self.notify(
                "No server configured. Add one in Settings.",
                severity="warning",
                timeout=6.0,
            )
        for server in self.config.servers:
            self.run_worker(self.server_registry.connect(server.name), exclusive=False)

    async def on_unmount(self) -> None:
        await self.server_registry.disconnect_all()

    # ── navigation ────────────────────────────────────────────────────────────

    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        """Handle tab selection — update ContentSwitcher."""
        if event.tab and event.tab.id:
            screen_id = event.tab.id
            self._current_screen = screen_id
            try:
                self.query_one("#content-area", ContentSwitcher).current = screen_id
            except Exception:
                pass

    def _switch_to(self, screen_id: str) -> None:
        """Switch to a screen by ID, syncing both Tabs and ContentSwitcher."""
        self._current_screen = screen_id
        try:
            # Setting tabs.active fires on_tabs_tab_activated which updates ContentSwitcher.
            # Set ContentSwitcher directly as well to handle startup edge-cases.
            self.query_one("#nav-tabs", Tabs).active = screen_id
        except Exception:
            pass
        try:
            self.query_one("#content-area", ContentSwitcher).current = screen_id
        except Exception:
            pass

    def _focus_content(self) -> None:
        """Move keyboard focus into the active content widget."""
        try:
            current_id = self.query_one("#content-area", ContentSwitcher).current
            if current_id:
                self.query_one(f"#{current_id}").focus()
        except Exception:
            pass

    # ── actions ───────────────────────────────────────────────────────────────

    def action_goto(self, screen_id: str) -> None:
        self._switch_to(screen_id)
        self.call_after_refresh(self._focus_content)

    def action_force_refresh(self) -> None:
        for server in self.config.servers:
            self.run_worker(self.server_registry.connect(server.name), exclusive=False)

    def action_show_shortcuts(self) -> None:
        from .screens.modals.shortcuts import ShortcutsModal
        self.push_screen(ShortcutsModal())

    # ── cross-screen messages ─────────────────────────────────────────────────

    def on_dashboard_navigate_to_models(self, _event: Dashboard.NavigateToModels) -> None:
        self._switch_to("models")
        self.call_after_refresh(self._focus_content)


# ── factory ───────────────────────────────────────────────────────────────────

def create_app(endpoint: str | None = None, api_key: str | None = None) -> LMStudioApp:
    needs_onboarding = False

    if not config_exists():
        if endpoint:
            config = create_default_config(endpoint, api_key or "")
        else:
            config = AppConfig(servers=[ServerConfig()])
            needs_onboarding = True
    else:
        config = load_config()
        if endpoint:
            active = config.active_server_config
            active.endpoint = endpoint
            if api_key is not None:
                active.api_key = api_key

    return LMStudioApp(config, needs_onboarding=needs_onboarding)