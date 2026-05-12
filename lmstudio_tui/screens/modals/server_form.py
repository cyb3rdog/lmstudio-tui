from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label

from ...config.models import ServerConfig


class ServerFormModal(ModalScreen[ServerConfig | None]):
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
            try:
                name = self.query_one("#inp-name", Input).value.strip() or "default"
                endpoint = self.query_one("#inp-endpoint", Input).value.strip() or "http://localhost:1234"
                api_key = self.query_one("#inp-apikey", Input).value.strip()
            except Exception:
                return
            self.dismiss(ServerConfig(name=name, endpoint=endpoint, api_key=api_key))
        else:
            self.dismiss(None)
