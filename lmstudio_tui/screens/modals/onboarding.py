from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label

from ...config.models import ServerConfig


class OnboardingModal(ModalScreen[ServerConfig | None]):
    """First-run welcome dialog. Collects endpoint + optional API key."""

    DEFAULT_CSS = """
    OnboardingModal > Vertical {
        background: $surface;
        border: thick $primary;
        width: 64;
        height: auto;
        padding: 2 3;
        align: center middle;
    }
    OnboardingModal Label { margin-bottom: 1; }
    OnboardingModal Input { margin-bottom: 1; }
    OnboardingModal Horizontal { height: auto; align: center middle; margin-top: 1; }
    OnboardingModal Button { margin: 0 1; }
    """

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("[bold]Welcome to LM Studio TUI[/bold]")
            yield Label(
                "Enter the address of your LM Studio server.\n"
                "Leave API key blank if authentication is disabled.",
                markup=False,
            )
            yield Label("Server endpoint")
            yield Input(value="http://localhost:1234", id="inp-endpoint")
            yield Label("API key (optional)")
            yield Input(placeholder="lms_...", password=True, id="inp-apikey")
            with Horizontal():
                yield Button("Connect", variant="primary", id="btn-connect")
                yield Button("Skip", id="btn-skip")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-connect":
            endpoint = self.query_one("#inp-endpoint", Input).value.strip() or "http://localhost:1234"
            api_key = self.query_one("#inp-apikey", Input).value.strip()
            self.dismiss(ServerConfig(name="default", endpoint=endpoint, api_key=api_key))
        else:
            self.dismiss(None)
