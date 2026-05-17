from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import Button, DataTable
from textual import work

from ..config.models import ModelPref
from ..config.loader import save_config
from ..utils.formatting import format_ctx
from .modals.confirm_dialog import ConfirmModal
from .modals.model_load import ModelLoadModal


class ModelManager(Widget):
    """Manage loaded and unloaded models on the server: load, unload, refresh."""

    BINDINGS = [
        ("l", "load_model",   "Load"),
        ("u", "unload_model", "Unload"),
        ("r", "refresh",      "Refresh"),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._focused_id: str | None = None
        self._loaded_ids: set[str] = set()

    def compose(self) -> ComposeResult:
        yield DataTable(id="models-table", cursor_type="row")
        with Horizontal(id="toolbar"):
            yield Button("↑ Load",     id="btn-load",    variant="primary")
            yield Button("↓ Unload",   id="btn-unload",  variant="default")
            yield Button("↺ Refresh",  id="btn-refresh", variant="default")

    def on_mount(self) -> None:
        self._setup_columns(self.query_one("#models-table", DataTable))
        self.action_refresh()

    def on_show(self) -> None:
        self.action_refresh()

    def _setup_columns(self, table: DataTable) -> None:
        table.add_column("St",    width=2)
        table.add_column("Model", width=36)
        table.add_column("Quant", width=8)
        table.add_column("Ctx",   width=5)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.data_table.id == "models-table" and event.row_key:
            self._focused_id = (
                str(event.row_key.value) if event.row_key.value is not None else None
            )

    # ── button dispatcher ─────────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "btn-load":    self.action_load_model()
            case "btn-unload":  self.action_unload_model()
            case "btn-refresh": self.action_refresh()

    # ── actions ───────────────────────────────────────────────────────────────

    @work
    async def action_refresh(self) -> None:
        try:
            client = await self.app.server_registry.wait_for_client()
            models = await client.list_models()
            self._loaded_ids = {m.id for m in models if m.is_loaded}
            table = self.query_one("DataTable")
            table.clear()
            for m in models:
                status = "●" if m.is_loaded else "○"
                quant  = m.quantization or "—"
                ctx    = format_ctx(m.max_context_length or m.context_length)
                table.add_row(status, m.id[:36], quant[:8], ctx, key=m.id)
            table.refresh()
        except Exception as e:
            self.notify(str(e), severity="error")

    @work
    async def action_load_model(self) -> None:
        model_id = self._focused_id
        if not model_id:
            self.app.notify("Select a model row first", severity="warning", timeout=4.0)
            return
        if model_id in self._loaded_ids:
            self.notify(f"'{model_id}' is already loaded", severity="warning", timeout=4.0)
            return
        pref = self.app.config.model_prefs.get(model_id)
        result = await self.app.push_screen_wait(
            ModelLoadModal(
                model_id,
                gpu_layers=pref.gpu_layers if pref else None,
                context_length=pref.context_length if pref else None,
            )
        )
        if result:
            self._do_load(result)

    @work
    async def action_unload_model(self) -> None:
        model_id = self._focused_id
        if not model_id:
            self.app.notify("Select a model row first", severity="warning", timeout=4.0)
            return
        confirmed = await self.app.push_screen_wait(
            ConfirmModal(f"Unload '{model_id}'?", "Unload Model")
        )
        if confirmed:
            self._do_unload(model_id)

    # ── helpers ───────────────────────────────────────────────────────────────

    @work
    async def _do_load(self, request) -> None:
        client = self.app.server_registry.active_client
        if not client:
            return
        try:
            self.notify(f"Loading {request.model}…")
            await client.load_model(request)
            self.app.config.model_prefs[request.model] = ModelPref(
                gpu_layers=request.gpu_layers,
                context_length=request.context_length,
            )
            save_config(self.app.config)
            self.notify(f"Loaded {request.model}", severity="information")
            self.action_refresh()
        except Exception as e:
            self.notify(str(e), severity="error")

    @work
    async def _do_unload(self, model_id: str) -> None:
        client = self.app.server_registry.active_client
        if not client:
            return
        try:
            # Fast path: instance_id may be cached in the server registry.
            # Fall back to list_models() only if not found.
            conn = self.app.server_registry.active_connection
            instance_id: str | None = None
            if conn:
                cached = next(
                    (m.instance_id for m in conn.models if m.id == model_id),
                    None,
                )
                if cached:
                    instance_id = cached
            if not instance_id:
                models = await client.list_models()
                instance_id = next(
                    (m.instance_id for m in models if m.id == model_id and m.instance_id),
                    None,
                )
            if not instance_id:
                self.notify(f"No loaded instance found for {model_id}", severity="warning")
                return
            await client.unload_model(instance_id)
            self.action_refresh()
            self.notify(f"Unloaded {model_id}", severity="information")
        except Exception as e:
            self.notify(str(e), severity="error")
