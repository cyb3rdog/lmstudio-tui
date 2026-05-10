from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Collapsible
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label

from ...api.models import LoadRequest


class ModelLoadModal(ModalScreen[LoadRequest | None]):
    DEFAULT_CSS = """
    ModelLoadModal > Vertical {
        background: $surface;
        border: thick $primary;
        width: 60;
        height: auto;
        padding: 1 2;
        align: center middle;
    }
    ModelLoadModal Label { margin-top: 1; }
    ModelLoadModal Horizontal { height: auto; align: center middle; margin-top: 1; }
    ModelLoadModal Button { margin: 0 1; }
    """

    def __init__(self, model_id: str) -> None:
        super().__init__()
        self._model_id = model_id

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(f"[bold]Load Model[/bold]")
            yield Label(f"[dim]{self._model_id}[/dim]")
            with Collapsible(title="Advanced options", collapsed=True):
                yield Label("GPU layers (-1 = full offload)")
                yield Input(placeholder="-1", id="inp-gpu-layers")
                yield Label("Context length (blank = model default)")
                yield Input(placeholder="", id="inp-ctx")
            with Horizontal():
                yield Button("Load", variant="primary", id="btn-load")
                yield Button("Cancel", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-load":
            gpu_raw = self.query_one("#inp-gpu-layers", Input).value.strip()
            ctx_raw = self.query_one("#inp-ctx", Input).value.strip()
            gpu_layers = int(gpu_raw) if gpu_raw else None
            ctx = int(ctx_raw) if ctx_raw else None
            self.dismiss(LoadRequest(model=self._model_id, gpu_layers=gpu_layers, context_length=ctx))
        else:
            self.dismiss(None)
