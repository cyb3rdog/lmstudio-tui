from __future__ import annotations

import asyncio

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

    DEFAULT_CSS = """
    ModelManager {
        width: 1fr;
        height: 1fr;
    }
    ModelManager DataTable { height: 1fr; }
    ModelManager #toolbar {
        height: 3;
        padding: 0 1;
        background: $surface-darken-1;
        border-top: solid $primary-darken-3;
    }
    ModelManager Button { margin: 0 1 0 0; }
    """

    BINDINGS = [
        ("l", "load_model",   "Load"),
        ("u", "unload_model", "Unload"),
        ("d", "goto_downloads", "Downloads"),
        ("r", "refresh",      "Refresh"),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._focused_id: str | None = None

    def compose(self) -> ComposeResult:
        yield DataTable(id="models-table", cursor_type="row")
        with Horizontal(id="toolbar"):
            yield Button("Load [L]",   id="btn-load",    variant="primary")
            yield Button("Unload [U]", id="btn-unload",  variant="default")
            yield Button("Downloads [D]", id="btn-downloads", variant="default")
            yield Button("Refresh [R]", id="btn-refresh", variant="default")

    def on_mount(self) -> None:
        self._setup_columns(self.query_one("#models-table", DataTable))
        self.action_refresh()

    def _setup_columns(self, table: DataTable) -> None:
        w = self.size.width
        if w < 50:
            table.add_column("Model", width=22)
            table.add_column("St",    width=2)
        elif w < 72:
            table.add_column("Model", width=20)
            table.add_column("St",    width=2)
            table.add_column("Quant", width=8)
            table.add_column("Ctx",   width=5)
        else:
            table.add_column("Model",  width=36)
            table.add_column("Status", width=8)
            table.add_column("Quant",  width=10)
            table.add_column("Ctx",    width=6)
            table.add_column("VRAM",   width=6)

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
            case "btn-downloads": self.action_goto_downloads()
            case "btn-refresh": self.action_refresh()

    # ── actions ───────────────────────────────────────────────────────────────

    def action_goto_downloads(self) -> None:
        """Navigate to the Downloads screen to browse and download models."""
        self.app.action_goto("downloads")

    @work
    async def action_refresh(self) -> None:
        client = self.app.server_registry.active_client
        if not client:
            for _ in range(20):
                await asyncio.sleep(0.25)
                client = self.app.server_registry.active_client
                if client:
                    break
        if not client:
            return
        try:
            models = await client.list_models()
            table = self.query_one("#models-table", DataTable)
            table.clear()
            col_count = len(table.columns)
            for m in models:
                status = "●" if m.is_loaded else "○"
                quant  = m.quantization or "—"
                ctx    = format_ctx(m.max_context_length or m.context_length)
                if col_count == 2:
                    table.add_row(m.id[:22], status, key=m.id)
                elif col_count == 4:
                    table.add_row(m.id[:20], status, quant[:8], ctx, key=m.id)
                else:
                    table.add_row(m.id[:36], status, quant[:10], ctx, "—", key=m.id)
            table.refresh()
        except Exception as e:
            self.notify(str(e), severity="error")

    @work
    async def action_load_model(self) -> None:
        model_id = self._focused_id
        if not model_id:
            self.app.notify("Select a model row first", severity="warning", timeout=4.0)
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
