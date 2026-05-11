from __future__ import annotations

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import ContentSwitcher, Footer, Header, Label, ListItem, ListView, Static

from .config.loader import config_exists, create_default_config, load_config, save_config
from .config.models import AppConfig, ServerConfig
from .screens.benchmark_runner import BenchmarkRunner
from .screens.chat import ChatScreen
from .screens.dashboard import Dashboard
from .screens.live_monitor import LiveMonitor
from .screens.model_manager import ModelManager
from .screens.settings import Settings
from .state.metrics_store import MetricsStore
from .state.server_registry import ConnectionState, ServerRegistry

# (key, label, shortcut-hint)
_NAV_ITEMS = [
    ("dashboard",  "Dashboard",  "1"),
    ("models",     "Models",     "2"),
    ("chat",       "Chat",       "3"),
    ("monitor",    "Monitor",    "4"),
    ("benchmark",  "Benchmark",  "5"),
    ("settings",   "Settings",  "6"),
]

# Sidebar auto-collapses below this terminal width
_PORTRAIT_WIDTH = 70

# Number-key labels shown in the portrait mini header
_NAV_KEYS = " ".join(f"[{h}]" for _, _, h in _NAV_ITEMS)

# Map screen key → display label for mini-header
_SCREEN_LABELS = {key: label for key, label, _ in _NAV_ITEMS}


class LMStudioApp(App[None]):
    TITLE = "LM Studio TUI"
    CSS_PATH = "app.tcss"

    BINDINGS = [
        Binding("ctrl+q",         "quit",             "Quit",            show=True),
        Binding("ctrl+b",         "toggle_sidebar",   "Menu",            show=True),
        Binding("escape",         "focus_nav",        "Nav",             show=True),
        Binding("question_mark",  "show_shortcuts",   "Help",            show=True),
        Binding("ctrl+r",         "force_refresh",    "Refresh",         show=False),
        # Number-key shortcuts always work regardless of sidebar state
        Binding("1", "goto('dashboard')",  "Dashboard",  show=False),
        Binding("2", "goto('models')",     "Models",     show=False),
        Binding("3", "goto('chat')",       "Chat",       show=False),
        Binding("4", "goto('monitor')",    "Monitor",    show=False),
        Binding("5", "goto('benchmark')",  "Benchmark",  show=False),
        Binding("6", "goto('settings')",   "Settings",   show=False),
    ]

    sidebar_visible: reactive[bool] = reactive(True, init=False)

    def __init__(self, config: AppConfig, needs_onboarding: bool = False) -> None:
        super().__init__()
        self.config = config
        self.server_registry = ServerRegistry(config.servers, active_server=config.active_server)
        self.metrics_store = MetricsStore()
        self._needs_onboarding = needs_onboarding
        self._current_screen = "dashboard"

    # ── layout ────────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main-layout"):
            with Vertical(id="sidebar"):
                yield Label("  LM Studio TUI", id="sidebar-title")
                yield ListView(
                    *[
                        ListItem(Label(f"  {label}  [{hint}]"), name=key)
                        for key, label, hint in _NAV_ITEMS
                    ],
                    id="nav-list",
                )
            with ContentSwitcher(initial="dashboard", id="content-area"):
                yield Dashboard(id="dashboard")
                yield ModelManager(id="models")
                yield ChatScreen(id="chat")
                yield LiveMonitor(id="monitor")
                yield BenchmarkRunner(id="benchmark")
                yield Settings(id="settings")
        yield Footer()
        # Portrait mini header — visible only when sidebar is collapsed.
        # Shows server state, current screen name, and number-key hints.
        yield Static("LM Studio TUI", id="mini-header")

    # ── lifecycle ─────────────────────────────────────────────────────────────

    async def on_mount(self) -> None:
        if self.size.width < _PORTRAIT_WIDTH:
            self.sidebar_visible = False

        nav = self.query_one("#nav-list", ListView)
        nav.focus()
        nav.index = 0

        self._update_mini_header()

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
            self.server_registry = ServerRegistry(self.config.servers)
        for server in self.config.servers:
            self.run_worker(self.server_registry.connect(server.name), exclusive=False)

    async def on_unmount(self) -> None:
        await self.server_registry.disconnect_all()

    def on_resize(self) -> None:
        if self.size.width < _PORTRAIT_WIDTH:
            self.sidebar_visible = False
        elif self.size.width >= _PORTRAIT_WIDTH and not self.sidebar_visible:
            self.sidebar_visible = True
        self._update_mini_header()

    # ── sidebar + mini-header reactivity ─────────────────────────────────────

    def watch_sidebar_visible(self, visible: bool) -> None:
        try:
            self.query_one("#sidebar").display = visible
            self.query_one("#mini-header").display = not visible
            self._update_mini_header()
        except Exception:
            pass

    def _update_mini_header(self) -> None:
        try:
            mini = self.query_one("#mini-header", Static)
            conn = self.server_registry.active_connection
            screen_label = _SCREEN_LABELS.get(self._current_screen, "")
            w = self.size.width

            icon = "○"
            if conn:
                icon = {
                    ConnectionState.CONNECTED:    "●",
                    ConnectionState.CONNECTING:   "◌",
                    ConnectionState.DISCONNECTED: "○",
                    ConnectionState.ERROR:        "✗",
                }.get(conn.state, "○")

            if w < 50:
                # Very narrow: just screen name + minimal nav hint
                mini.update(f"[bold]{screen_label}[/bold]  [dim]{_NAV_KEYS}[/dim]")
            elif w < 70:
                # Narrow: status icon + screen name + nav keys
                mini.update(f"{icon}  [bold]{screen_label}[/bold]  [dim]{_NAV_KEYS}[/dim]")
            else:
                # Wide portrait: server name + screen + keys
                server_name = self.server_registry.active_name
                mini.update(
                    f"{icon} {server_name}  [bold]{screen_label}[/bold]  [dim]{_NAV_KEYS}[/dim]"
                )
        except Exception:
            pass

    # ── navigation ────────────────────────────────────────────────────────────

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Switch screens as arrow keys move the highlight."""
        if event.list_view.id == "nav-list" and event.item and event.item.name:
            self._switch_to(event.item.name)
            if not self.sidebar_visible:
                self._focus_content()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Enter / Space: switch screen and move focus into content area.

        On portrait/mobile (sidebar was auto-collapsed) collapse after selection
        so the content fills the screen.
        """
        if event.list_view.id == "nav-list" and event.item and event.item.name:
            self._switch_to(event.item.name)
            # Auto-collapse on portrait so content has full width
            if self.size.width < _PORTRAIT_WIDTH:
                self.sidebar_visible = False
            self._focus_content()

    def _switch_to(self, screen_id: str) -> None:
        self.query_one("#content-area", ContentSwitcher).current = screen_id
        self._current_screen = screen_id
        nav = self.query_one("#nav-list", ListView)
        for i, (key, _, _) in enumerate(_NAV_ITEMS):
            if key == screen_id:
                nav.index = i
                break
        self._update_mini_header()

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
        """Escape — smart sidebar toggle.

        - If sidebar is hidden  → expand it (if wide enough) and focus nav.
        - If sidebar is visible and nav already has focus → collapse it and
          move focus to content (Escape acts as a second toggle).
        - Otherwise → just focus nav without changing sidebar state.
        """
        nav = self.query_one("#nav-list", ListView)
        if not self.sidebar_visible:
            if self.size.width >= _PORTRAIT_WIDTH:
                self.sidebar_visible = True
            nav.focus()
        elif nav.has_focus:
            # Second Escape while nav is focused → collapse sidebar
            self.sidebar_visible = False
            self._focus_content()
        else:
            nav.focus()

    def action_goto(self, screen_id: str) -> None:
        self._switch_to(screen_id)

    def action_force_refresh(self) -> None:
        for server in self.config.servers:
            self.run_worker(self.server_registry.connect(server.name), exclusive=False)

    def action_show_shortcuts(self) -> None:
        from .screens.modals.shortcuts import ShortcutsModal
        self.push_screen(ShortcutsModal())

    # ── dashboard messages ────────────────────────────────────────────────────

    def on_dashboard_navigate_to_models(self, _event: Dashboard.NavigateToModels) -> None:
        self._switch_to("models")
        self._focus_content()


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
