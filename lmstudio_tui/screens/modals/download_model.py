from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static


class DownloadModelModal(ModalScreen[str | None]):
    """Prompt for a model ID to download from HuggingFace / LM Studio catalogue.

    Returns the model ID string on confirm, None on cancel.
    """

    DEFAULT_CSS = """
    DownloadModelModal > Vertical {
        background: $surface;
        border: thick $primary;
        width: 90%;
        max-width: 64;
        height: auto;
        padding: 1 2;
        align: center middle;
    }
    DownloadModelModal Label { margin-top: 1; }
    DownloadModelModal .hint {
        color: $text-muted;
        margin-top: 0;
    }
    DownloadModelModal Input { margin-top: 1; margin-bottom: 1; }
    DownloadModelModal Horizontal { height: auto; align: center middle; margin-top: 1; }
    DownloadModelModal Button { margin: 0 1; }
    """

    BINDINGS = [("escape", "dismiss_modal", "Cancel")]

    def __init__(self, prefill: str = "") -> None:
        super().__init__()
        self._prefill = prefill

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("[bold]Download Model[/bold]")
            yield Label("Enter a model ID from HuggingFace or the LM Studio catalogue.")
            yield Static(
                "  Examples:\n"
                "  [dim]lmstudio-community/Meta-Llama-3-8B-Instruct-GGUF[/dim]\n"
                "  [dim]bartowski/Phi-3-mini-4k-instruct-GGUF[/dim]",
                classes="hint",
            )
            yield Label("Model ID")
            yield Input(
                value=self._prefill,
                placeholder="author/model-name-GGUF",
                id="inp-model-id",
            )
            with Horizontal():
                yield Button("Download", variant="primary", id="btn-download")
                yield Button("Cancel", id="btn-cancel")

    def on_mount(self) -> None:
        self.query_one("#inp-model-id", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-download":
            model_id = self.query_one("#inp-model-id", Input).value.strip()
            if not model_id:
                self.notify("Enter a model ID", severity="warning")
                return
            self.dismiss(model_id)
        else:
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        model_id = event.value.strip()
        if not model_id:
            self.notify("Enter a model ID", severity="warning")
            return
        self.dismiss(model_id)

    def action_dismiss_modal(self) -> None:
        self.dismiss(None)
