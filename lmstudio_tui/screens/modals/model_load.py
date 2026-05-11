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
        width: 90%;
        max-width: 60;
        height: auto;
        padding: 1 2;
        align: center middle;
    }
    ModelLoadModal Label { margin-top: 1; }
    ModelLoadModal Horizontal { height: auto; align: center middle; margin-top: 1; }
    ModelLoadModal Button { margin: 0 1; }
    """

    def __init__(
        self,
        model_id: str,
        gpu_layers: int | None = None,
        context_length: int | None = None,
    ) -> None:
        super().__init__()
        self._model_id = model_id
        self._saved_gpu = gpu_layers
        self._saved_ctx = context_length

    def compose(self) -> ComposeResult:
        gpu_val = str(self._saved_gpu) if self._saved_gpu is not None else ""
        ctx_val = str(self._saved_ctx) if self._saved_ctx is not None else ""
        # Expand Advanced options if saved prefs exist
        collapsed = self._saved_gpu is None and self._saved_ctx is None
        with Vertical():
            yield Label("[bold]Load Model[/bold]")
            yield Label(f"[dim]{self._model_id}[/dim]")
            with Collapsible(title="Advanced options", collapsed=collapsed):
                yield Label("GPU layers  (0 = CPU only · -1 = full GPU offload)")
                yield Input(value=gpu_val, placeholder="-1", id="inp-gpu-layers")
                yield Label("Context length  (blank = model default)")
                yield Input(value=ctx_val, placeholder="", id="inp-ctx")
            with Horizontal():
                yield Button("Load", variant="primary", id="btn-load")
                yield Button("Cancel", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-load":
            try:
                gpu_raw = self.query_one("#inp-gpu-layers", Input).value.strip()
                ctx_raw = self.query_one("#inp-ctx", Input).value.strip()
            except Exception:
                return
            try:
                gpu_layers = int(gpu_raw) if gpu_raw else None
                ctx = int(ctx_raw) if ctx_raw else None
            except ValueError:
                self.notify("GPU layers and context must be integers", severity="error")
                return
            self.dismiss(LoadRequest(model=self._model_id, gpu_layers=gpu_layers, context_length=ctx))
        else:
            self.dismiss(None)
