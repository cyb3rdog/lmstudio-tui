from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class ConfirmModal(ModalScreen[bool]):
    DEFAULT_CSS = """
    ConfirmModal > Vertical {
        background: $surface;
        border: thick $primary;
        width: 50;
        height: auto;
        padding: 1 2;
        align: center middle;
    }
    ConfirmModal Label { margin-bottom: 1; }
    ConfirmModal Horizontal { height: auto; align: center middle; }
    ConfirmModal Button { margin: 0 1; }
    """

    def __init__(self, message: str, title: str = "Confirm") -> None:
        super().__init__()
        self._message = message
        self._title = title

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(f"[bold]{self._title}[/bold]")
            yield Label(self._message)
            with Horizontal():
                yield Button("Yes", variant="error", id="btn-yes")
                yield Button("No", variant="default", id="btn-no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "btn-yes")
