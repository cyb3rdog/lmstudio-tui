from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import ContentSwitcher, Footer, Header, Label, ListItem, ListView

from .config.loader import config_exists, create_default_config, load_config, save_config
from .config.models import AppConfig, ServerConfig
from .screens.benchmark_runner import BenchmarkRunner
from .screens.dashboard import Dashboard
from .screens.live_monitor import LiveMonitor
from .screens.model_manager import ModelManager
from .screens.settings import Settings
from .state.metrics_store import MetricsStore
from .state.server_registry import ServerRegistry

# (key, screen-id, label, shortcut-hint)
_NAV_ITEMS = [
    ("dashboard",  "  Dashboard",  "1"),
    ("models",     "  Models",     "2"),
    ("monitor",    "  Monitor",    "3"),
    ("benchmark",  "  Benchmark",  "4"),
    ("settings",   "  Settings",   "5"),
]

# Sidebar auto-collapses below this terminal width
_PORTRAIT_WIDTH = 70


class LMStudioApp(App[None]):
    TITLE = "LM Studio TUI"
    CSS_PATH = "app.tcss"

    BINDINGS = [
        Binding("ctrl+q",         "quit",             "Quit",            show=True),
        Binding("ctrl+b",         "toggle_sidebar",   "Menu",            show=True),
        Binding("escape",         "focus_nav",        "Back",            show=True),
        Binding("ctrl+r",         "force_refresh",    "Refresh",         show=False),
        # Number-key shortcuts always work regardless of sidebar state
        Binding("1", "goto('dashboard')",  "Dashboard",  show=False),
        Binding("2", "goto('models')",     "Models",     show=False),
        Binding("3", "goto('monitor')",    "Monitor",    show=False),
        Binding("4", "goto('benchmark')",  "Benchmark",  show=False),
        Binding("5", "goto('settings')",   "Settings",   show=False),
    ]

    sidebar_visible: reactive[bool] = reactive(True, init=False)

    def __init__(self, config: AppConfig, needs_onboarding: bool = False) -> None:
        super().__init__()
        self.config = config
        self.server_registry = ServerRegistry(config.servers)
        self.metrics_store = MetricsStore()
        self._needs_onboarding = needs_onboarding

    # ── layout ────────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main-layout"):
            with Vertical(id="sidebar"):
                yield Label("  LM Studio TUI", id="sidebar-title")
                yield ListView(
                    *[
                        ListItem(Label(f"{label}  [{hint}]"), name=key)
                        for key, label, hint in _NAV_ITEMS
                    ],
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
        # Auto-collapse sidebar on narrow terminals
        if self.size.width < _PORTRAIT_WIDTH:
            self.sidebar_visible = False

        # Focus nav list
        nav = self.query_one("#nav-list", ListView)
        nav.focus()
        nav.index = 0

        if self._needs_onboarding:
            # push_screen_wait requires a worker context
            self.run_worker(self._run_onboarding(), exclusive=True)
        else:
            # Connect to servers in background
            for server in self.config.servers:
                self.run_worker(self.server_registry.connect(server.name), exclusive=False)

    async def _run_onboarding(self) -> None:
        from .screens.modals.onboarding import OnboardingModal
        server_cfg = await self.push_screen_wait(OnboardingModal())
        if server_cfg is not None:
            self.config.servers = [server_cfg]
            self.config.active_server = server_cfg.name
            save_config(self.config)
            self.server_registry = ServerRegistry(self.config.servers)
        # Connect after onboarding (whether config was set or not)
        for server in self.config.servers:
            self.run_worker(self.server_registry.connect(server.name), exclusive=False)

    async def on_unmount(self) -> None:
        await self.server_registry.disconnect_all()

    def on_resize(self) -> None:
        """Auto-collapse sidebar when terminal is too narrow for side-by-side layout."""
        if self.size.width < _PORTRAIT_WIDTH:
            self.sidebar_visible = False
        elif self.size.width >= _PORTRAIT_WIDTH and not self.sidebar_visible:
            # Restore sidebar when terminal widens again
            self.sidebar_visible = True

    # ── sidebar reactivity ────────────────────────────────────────────────────

    def watch_sidebar_visible(self, visible: bool) -> None:
        try:
            sidebar = self.query_one("#sidebar")
            sidebar.display = visible
        except Exception:
            pass

    # ── navigation ────────────────────────────────────────────────────────────

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Switch screens immediately as the highlight moves (arrow keys)."""
        if event.list_view.id == "nav-list" and event.item and event.item.name:
            self._switch_to(event.item.name)
            if not self.sidebar_visible:
                self._focus_content()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Enter / Space: move focus into content area."""
        if event.list_view.id == "nav-list" and event.item and event.item.name:
            self._switch_to(event.item.name)
            if not self.sidebar_visible:
                self._focus_content()

    def _switch_to(self, screen_id: str) -> None:
        self.query_one("#content-area", ContentSwitcher).current = screen_id
        # Keep nav index in sync
        nav = self.query_one("#nav-list", ListView)
        for i, (key, _, _) in enumerate(_NAV_ITEMS):
            if key == screen_id:
                nav.index = i
                break

    def _focus_content(self) -> None:
        """Move keyboard focus into the active content widget."""
        try:
            current_id = self.query_one("#content-area", ContentSwitcher).current
            if current_id:
                self.query_one(f"#{current_id}").focus()
        except Exception:
            pass

    # ── actions ───────────────────────────────────────────────────────────────

    def action_toggle_sidebar(self) -> None:
        self.sidebar_visible = not self.sidebar_visible
        if self.sidebar_visible:
            self.query_one("#nav-list", ListView).focus()
        else:
            self._focus_content()

    def action_focus_nav(self) -> None:
        """Escape/Back — return focus to sidebar nav list, expanding it if hidden."""
        if not self.sidebar_visible and self.size.width >= _PORTRAIT_WIDTH:
            self.sidebar_visible = True
        self.query_one("#nav-list", ListView).focus()

    def action_goto(self, screen_id: str) -> None:
        self._switch_to(screen_id)

    def action_force_refresh(self) -> None:
        for server in self.config.servers:
            self.run_worker(self.server_registry.connect(server.name), exclusive=False)


# ── factory ───────────────────────────────────────────────────────────────────

def create_app(endpoint: str | None = None, api_key: str | None = None) -> LMStudioApp:
    needs_onboarding = False

    if not config_exists():
        if endpoint:
            # CLI-supplied endpoint: create config silently, no onboarding
            config = create_default_config(endpoint, api_key or "")
        else:
            # No config, no CLI args: use bare defaults, trigger onboarding in-app
            config = AppConfig(servers=[ServerConfig()])
            needs_onboarding = True
    else:
        config = load_config()
        if endpoint:
            # CLI override: patch active server at runtime (not persisted)
            active = config.active_server_config
            active.endpoint = endpoint
            if api_key is not None:
                active.api_key = api_key

    return LMStudioApp(config, needs_onboarding=needs_onboarding)
