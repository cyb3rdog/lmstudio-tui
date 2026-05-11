from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label

from ...config.models import ServerConfig


class ServerFormModal(ModalScreen[ServerConfig | None]):
    DEFAULT_CSS = """
    ServerFormModal > Vertical {
        background: $surface;
        border: thick $primary;
        width: 90%;
        max-width: 60;
        height: auto;
        padding: 1 2;
        align: center middle;
    }
    ServerFormModal Label { margin-top: 1; }
    ServerFormModal Input { margin-bottom: 1; }
    ServerFormModal Horizontal { height: auto; align: center middle; margin-top: 1; }
    ServerFormModal Button { margin: 0 1; }
    """

    def __init__(self, existing: ServerConfig | None = None) -> None:
        super().__init__()
        self._existing = existing

    def compose(self) -> ComposeResult:
        ex = self._existing
        with Vertical():
            yield Label("[bold]Server Connection[/bold]")
            yield Label("Display name")
            yield Input(value=ex.name if ex else "", placeholder="e.g. home-gpu", id="inp-name")
            yield Label("Endpoint URL")
            yield Input(
                value=ex.endpoint if ex else "http://localhost:1234",
                placeholder="http://host:1234",
                id="inp-endpoint",
            )
            yield Label("API Key (leave blank if not required)")
            yield Input(
                value=ex.api_key if ex else "",
                placeholder="lms_...",
                password=True,
                id="inp-apikey",
            )
            with Horizontal():
                yield Button("Save", variant="primary", id="btn-save")
                yield Button("Cancel", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save":
            name = self.query_one("#inp-name", Input).value.strip() or "default"
            endpoint = self.query_one("#inp-endpoint", Input).value.strip() or "http://localhost:1234"
            api_key = self.query_one("#inp-apikey", Input).value.strip()
            self.dismiss(ServerConfig(name=name, endpoint=endpoint, api_key=api_key))
        else:
            self.dismiss(None)
