from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.widget import Widget
from textual.widgets import Button, Input, Label, ListItem, ListView, Static
from textual import work

from ..config.loader import save_config
from ..config.models import ServerConfig
from ..state.server_registry import ServerRegistry
from .modals.confirm_dialog import ConfirmModal
from .modals.server_form import ServerFormModal


class Settings(Widget):
    DEFAULT_CSS = """
    Settings {
        width: 1fr;
        height: 1fr;
    }
    Settings #layout {
        height: 1fr;
    }
    Settings #server-panel {
        width: 36;
        border-right: solid $primary-darken-3;
        padding: 0 1;
    }
    Settings #prefs-panel {
        width: 1fr;
        padding: 0 2;
    }
    Settings .section-title {
        text-style: bold;
        margin-top: 1;
        margin-bottom: 1;
        color: $primary;
    }
    Settings ListView { height: 1fr; }
    Settings Button { margin: 0 0 1 0; width: 100%; }
    Settings #btn-row { height: auto; margin-bottom: 1; }
    Settings #btn-row Button { margin: 0 1 0 0; width: auto; }
    Settings .pref-label { margin-top: 1; color: $text-muted; }
    Settings Input { margin-bottom: 1; }
    """

    def compose(self) -> ComposeResult:
        with Horizontal(id="layout"):
            with Vertical(id="server-panel"):
                yield Label("Servers", classes="section-title")
                yield ListView(id="server-list")
                with Horizontal(id="btn-row"):
                    yield Button("+ Add", id="btn-add", variant="primary")
                    yield Button("Edit", id="btn-edit", variant="default")
                    yield Button("Remove", id="btn-remove", variant="error")
                yield Button("Test Connection", id="btn-test", variant="default")
                yield Static("", id="test-result")
            with ScrollableContainer(id="prefs-panel"):
                yield Label("App Preferences", classes="section-title")
                yield Label("Poll interval (seconds)", classes="pref-label")
                yield Input(id="inp-poll", placeholder="3.0")
                yield Label("Benchmark export directory", classes="pref-label")
                yield Input(id="inp-export-dir", placeholder="~/.lmstudio-tui/benchmarks")
                yield Button("Save Preferences", id="btn-save-prefs", variant="primary")

    def on_mount(self) -> None:
        self._load_server_list()
        self.query_one("#inp-poll", Input).value = str(self.app.config.ui.poll_interval_s)
        self.query_one("#inp-export-dir", Input).value = self.app.config.benchmark.export_dir

    def _load_server_list(self) -> None:
        lv = self.query_one("#server-list", ListView)
        lv.clear()
        for s in self.app.config.servers:
            conn = self.app.server_registry.get_connection(s.name)
            state_icon = "●" if conn and conn.state.value == "connected" else "○"
            lv.append(ListItem(Label(f"{state_icon} {s.name}  {s.endpoint}"), name=s.name))

    def _selected_server_name(self) -> str | None:
        lv = self.query_one("#server-list", ListView)
        if lv.highlighted_child:
            return lv.highlighted_child.name
        return None

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        btn = event.button.id
        if btn == "btn-add":
            result = await self.app.push_screen_wait(ServerFormModal())
            if result:
                self.app.config.servers.append(result)
                self.app.server_registry.add_server(result)
                save_config(self.app.config)
                self._load_server_list()
                self.app.call_later(lambda: self.app.server_registry.connect(result.name))

        elif btn == "btn-edit":
            name = self._selected_server_name()
            if not name:
                return
            existing = next((s for s in self.app.config.servers if s.name == name), None)
            result = await self.app.push_screen_wait(ServerFormModal(existing))
            if result:
                for i, s in enumerate(self.app.config.servers):
                    if s.name == name:
                        self.app.config.servers[i] = result
                        break
                save_config(self.app.config)
                self._load_server_list()

        elif btn == "btn-remove":
            name = self._selected_server_name()
            if not name:
                return
            confirmed = await self.app.push_screen_wait(ConfirmModal(f"Remove server '{name}'?"))
            if confirmed:
                self.app.config.servers = [s for s in self.app.config.servers if s.name != name]
                self.app.server_registry.remove_server(name)
                save_config(self.app.config)
                self._load_server_list()

        elif btn == "btn-test":
            name = self._selected_server_name()
            if name:
                self._test_connection(name)

        elif btn == "btn-save-prefs":
            try:
                poll = float(self.query_one("#inp-poll", Input).value or "3.0")
                self.app.config.ui.poll_interval_s = poll
            except ValueError:
                pass
            self.app.config.benchmark.export_dir = (
                self.query_one("#inp-export-dir", Input).value.strip()
                or "~/.lmstudio-tui/benchmarks"
            )
            save_config(self.app.config)
            self.notify("Preferences saved", severity="information")

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
