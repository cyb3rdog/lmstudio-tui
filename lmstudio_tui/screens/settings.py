from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.widget import Widget
from textual.widgets import Button, Input, Label, ListItem, ListView, Static
from textual import work

from ..config.loader import save_config
from ..config.models import ServerConfig
from ..constants import METRICS_WINDOW, NARROW_SCREEN_THRESHOLD
from .modals.confirm_dialog import ConfirmModal
from .modals.server_form import ServerFormModal


class Settings(Widget):
    """Settings screen: manage servers, set active server, app preferences."""

    # Debounce resize-triggered server list reloads.
    _resize_debounce: bool = False

    def compose(self) -> ComposeResult:
        with Horizontal(id="layout"):
            # ── Left panel: servers ────────────────────────────────────────
            with Vertical(id="server-panel"):
                yield Label("Servers", classes="section-title")
                yield ListView(id="server-list")
                with Horizontal(id="btn-row"):
                    yield Button("+ Add", id="btn-add",     variant="primary")
                    yield Button("Edit",  id="btn-edit",   variant="default")
                    yield Button("Remove", id="btn-remove", variant="error")
                with Horizontal(id="set-active-row"):
                    yield Button("Set Active", id="btn-set-active", variant="default")
                with Horizontal(id="test-row"):
                    yield Button("Test Connection", id="btn-test", variant="default")
                    yield Static("", id="test-result")

            # ── Right panel: preferences ─────────────────────────────────────
            with ScrollableContainer(id="prefs-panel"):
                yield Label("App Preferences", classes="section-title")

                with Vertical(id="poll-section"):
                    yield Label("Poll interval (seconds)", classes="pref-label")
                    yield Input(id="inp-poll", placeholder="3.0")

                with Vertical(id="timeout-section"):
                    yield Label("Request timeout (seconds)", classes="pref-label")
                    yield Input(id="inp-timeout", placeholder="900")

                with Vertical(id="window-section"):
                    yield Label("Metrics history (samples per model)", classes="pref-label")
                    yield Input(id="inp-window", placeholder="120")

                with Vertical(id="export-section"):
                    yield Label("Benchmark export directory", classes="pref-label")
                    yield Input(id="inp-export-dir", placeholder="~/.lmstudio-tui/benchmarks")

                with Horizontal(id="save-row"):
                    yield Button("Save Preferences", id="btn-save-prefs", variant="primary")

    def on_mount(self) -> None:
        self._resize_debounce = False
        self._load_server_list()
        self._load_prefs()
        self._update_layout()

    def on_resize(self) -> None:
        self._update_layout()
        # Debounce: reload server list only when not already pending.
        if not self._resize_debounce:
            self._resize_debounce = True
            self.call_next(self._load_server_list_and_reset_debounce)

    def _load_server_list_and_reset_debounce(self) -> None:
        self._resize_debounce = False
        self._load_server_list()

    def _update_layout(self) -> None:
        w = self.size.width
        try:
            layout = self.query_one("#layout")
            if w < NARROW_SCREEN_THRESHOLD:
                layout.add_class("stacked")
            else:
                layout.remove_class("stacked")
        except Exception:
            pass

    def _load_server_list(self) -> None:
        lv = self.query_one("#server-list", ListView)
        lv.clear()
        active = self.app.server_registry.active_name
        max_ep = max(20, self.size.width - 18)
        for s in self.app.config.servers:
            conn = self.app.server_registry.get_connection(s.name)
            state_icon = "●" if conn and conn.state.value == "connected" else "○"
            ep = s.endpoint if len(s.endpoint) <= max_ep else s.endpoint[:max_ep - 1] + "…"
            label = f"{state_icon} {s.name}  {ep}"
            if s.name == active:
                label = f"[bold yellow]★ {label}[/bold yellow]"
            lv.append(ListItem(Label(label), name=s.name))

    def _load_prefs(self) -> None:
        self.query_one("#inp-poll", Input).value       = str(self.app.config.ui.poll_interval_s)
        self.query_one("#inp-timeout", Input).value    = str(self.app.config.active_server_config.timeout_s)
        self.query_one("#inp-window", Input).value      = str(self.app.config.metrics_window)
        self.query_one("#inp-export-dir", Input).value  = self.app.config.benchmark.export_dir

    def _selected_server_name(self) -> str | None:
        lv = self.query_one("#server-list", ListView)
        if lv.highlighted_child:
            return lv.highlighted_child.name
        return None

    # ── button dispatcher ─────────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "btn-add":
                self._add_server()
            case "btn-edit":
                self._edit_server()
            case "btn-remove":
                self._remove_server()
            case "btn-set-active":
                self._set_active_server()
            case "btn-test":
                name = self._selected_server_name()
                if name:
                    self._test_connection(name)
                else:
                    self.notify("Select a server first", severity="warning")
            case "btn-save-prefs":
                self._save_prefs()

    # ── @work action methods (worker context allows push_screen_wait) ─────────

    @work
    async def _add_server(self) -> None:
        result = await self.app.push_screen_wait(ServerFormModal())
        if result:
            self.app.config.servers.append(result)
            self.app.server_registry.add_server(result)
            save_config(self.app.config)
            self._load_server_list()
            self.app.run_worker(self.app.server_registry.connect(result.name), exclusive=False)

    @work
    async def _edit_server(self) -> None:
        name = self._selected_server_name()
        if not name:
            self.notify("Select a server first", severity="warning")
            return
        existing = next((s for s in self.app.config.servers if s.name == name), None)
        result = await self.app.push_screen_wait(ServerFormModal(existing))
        if result:
            for i, s in enumerate(self.app.config.servers):
                if s.name == name:
                    self.app.config.servers[i] = result
                    break
            self.app.server_registry.add_server(result)
            save_config(self.app.config)
            self._load_server_list()

    @work
    async def _remove_server(self) -> None:
        name = self._selected_server_name()
        if not name:
            self.notify("Select a server first", severity="warning")
            return
        confirmed = await self.app.push_screen_wait(ConfirmModal(f"Remove server '{name}'?"))
        if confirmed:
            self.app.config.servers = [s for s in self.app.config.servers if s.name != name]
            self.app.server_registry.remove_server(name)
            save_config(self.app.config)
            self._load_server_list()

    @work
    async def _set_active_server(self) -> None:
        name = self._selected_server_name()
        if not name:
            self.notify("Select a server first", severity="warning")
            return
        self.app.config.active_server = name
        self.app.server_registry.active_name = name
        save_config(self.app.config)
        self._load_server_list()
        self.notify(f"Active server set to '{name}'", severity="information")

    @work
    async def _test_connection(self, name: str) -> None:
        result_label = self.query_one("#test-result", Static)
        result_label.update("  Testing…")
        conn = self.app.server_registry.get_connection(name)
        if not conn:
            result_label.update("  [red]Server not found[/red]")
            return
        try:
            from ..api.client import LMStudioClient
            async with LMStudioClient(conn.config) as client:
                ms = await client.ping()
            result_label.update(f"  [green]✓ Connected  {ms:.0f}ms[/green]")
        except Exception as e:
            result_label.update(f"  [red]✗ {e}[/red]")

    def _save_prefs(self) -> None:
        # ── Poll interval ────────────────────────────────────────────────
        try:
            poll = float(self.query_one("#inp-poll", Input).value or "3.0")
        except ValueError:
            self.notify("Poll interval must be a number", severity="error")
            return
        from ..constants import MIN_POLL_INTERVAL_S
        if poll < MIN_POLL_INTERVAL_S:
            self.notify(
                f"Poll interval must be ≥ {MIN_POLL_INTERVAL_S} s (clamped from {poll}).",
                severity="warning",
                timeout=4.0,
            )
            poll = MIN_POLL_INTERVAL_S
        self.app.config.ui.poll_interval_s = poll

        # ── Request timeout ──────────────────────────────────────────────
        try:
            timeout = float(self.query_one("#inp-timeout", Input).value or "900")
        except ValueError:
            self.notify("Request timeout must be a number", severity="error")
            return
        if timeout < 10.0:
            self.notify("Timeout must be ≥ 10 s (clamped).", severity="warning", timeout=4.0)
            timeout = 10.0
        elif timeout > 3600.0:
            timeout = 3600.0
        # Apply to active server config (in-memory + config file).
        self.app.config.active_server_config.timeout_s = timeout

        # ── Metrics window ────────────────────────────────────────────────
        try:
            win = int(self.query_one("#inp-window", Input).value or str(METRICS_WINDOW))
        except ValueError:
            self.notify("Metrics window must be an integer", severity="error")
            return
        if win < 10:
            self.notify("Metrics window must be ≥ 10 (clamped).", severity="warning", timeout=4.0)
            win = 10
        elif win > 500:
            win = 500
        self.app.config.metrics_window = win
        # Rebuild the ring buffer with the new window size.
        self.app.metrics_store._window = win

        # ── Export dir ────────────────────────────────────────────────────
        self.app.config.benchmark.export_dir = (
            self.query_one("#inp-export-dir", Input).value.strip()
            or "~/.lmstudio-tui/benchmarks"
        )

        save_config(self.app.config)
        # Apply poll interval immediately by restarting the Dashboard timer.
        self._apply_poll_interval(poll)
        self.notify("Preferences saved", severity="information")

    def _apply_poll_interval(self, interval: float) -> None:
        """Restart the Dashboard refresh timer with the new interval."""
        try:
            from .dashboard import Dashboard
            dash = self.app.query_one("#dashboard", Dashboard)
            dash._refresh_timer.stop()
            dash._refresh_timer = dash.set_interval(interval, dash._refresh)
        except Exception:
            pass