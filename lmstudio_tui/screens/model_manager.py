from __future__ import annotations

import asyncio

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Button, DataTable, Label, ProgressBar, Static
from textual import work

from ..config.models import ModelPref
from ..config.loader import save_config
from ..utils.formatting import format_ctx
from .modals.confirm_dialog import ConfirmModal
from .modals.download_model import DownloadModelModal
from .modals.model_load import ModelLoadModal


class ModelManager(Widget):
    DEFAULT_CSS = """
    ModelManager {
        width: 1fr;
        height: 1fr;
    }
    ModelManager #toolbar {
        height: 3;
        padding: 0 1;
        background: $surface-darken-1;
        border-bottom: solid $primary-darken-3;
    }
    ModelManager DataTable { height: 1fr; }
    ModelManager #dl-bar {
        height: 3;
        padding: 0 1;
        background: $surface-darken-1;
        border-top: solid $primary-darken-3;
        align: left middle;
    }
    ModelManager #dl-bar.-hidden { display: none; }
    ModelManager #dl-label { width: auto; margin-right: 1; }
    ModelManager #dl-progress { width: 1fr; }
    ModelManager #btn-dl-cancel { width: auto; margin-left: 1; }
    ModelManager Button { margin: 0 1; }
    """

    BINDINGS = [
        ("l", "load_model", "Load"),
        ("u", "unload_model", "Unload"),
        ("d", "download_model", "Download"),
        ("r", "refresh", "Refresh"),
    ]

    def compose(self) -> ComposeResult:
        with Horizontal(id="toolbar"):
            yield Button("Load [l]", id="btn-load", variant="primary")
            yield Button("Unload [u]", id="btn-unload", variant="default")
            yield Button("Download [d]", id="btn-download", variant="default")
            yield Button("Refresh [r]", id="btn-refresh", variant="default")
        yield DataTable(id="models-table", cursor_type="row")
        with Horizontal(id="dl-bar", classes="-hidden"):
            yield Label("Downloading: ", id="dl-label")
            yield ProgressBar(id="dl-progress", total=100, show_eta=False)
            yield Button("✕ Cancel", id="btn-dl-cancel", variant="error")

    def on_mount(self) -> None:
        table = self.query_one("#models-table", DataTable)
        self._setup_columns(table)
        self._dl_timer = None
        self._dl_client = None
        self._dl_model_id = ""
        self._update_toolbar_layout()
        self.action_refresh()

    def _setup_columns(self, table: DataTable) -> None:
        w = self.size.width
        if w < 50:
            table.add_column("Model", width=24)
            table.add_column("St", width=2)
        elif w < 70:
            table.add_column("Model", width=28)
            table.add_column("Status", width=7)
            table.add_column("Ctx", width=5)
        else:
            table.add_column("Model", width=40)
            table.add_column("Status", width=8)
            table.add_column("Quant", width=8)
            table.add_column("Ctx", width=6)
            table.add_column("VRAM", width=6)

    def on_unmount(self) -> None:
        if self._dl_timer:
            self._dl_timer.stop()

    def on_resize(self) -> None:
        self._update_toolbar_layout()

    def _update_toolbar_layout(self) -> None:
        try:
            toolbar = self.query_one("#toolbar")
            if self.size.width < 58:
                toolbar.add_class("stacked")
            else:
                toolbar.remove_class("stacked")
        except Exception:
            pass

    # ── sync dispatcher ───────────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "btn-load":
                self.action_load_model()
            case "btn-unload":
                self.action_unload_model()
            case "btn-download":
                self.action_download_model()
            case "btn-refresh":
                self.action_refresh()
            case "btn-dl-cancel":
                self._cancel_download()

    # ── actions (all decorated with @work so push_screen_wait is safe) ────────

    @work
    async def action_refresh(self) -> None:
        client = self.app.server_registry.active_client
        
        # Wait for connection to be established (fixes race condition RC1)
        if not client:
            # Poll until connected or timeout (5 seconds)
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
                quant = m.quantization or "—"
                ctx = format_ctx(m.max_context_length or m.context_length)
                if col_count == 2:
                    table.add_row(m.id[:24], status, key=m.id)
                elif col_count == 3:
                    table.add_row(m.id[:28], status, ctx, key=m.id)
                else:
                    table.add_row(m.id, status, quant, ctx, "—", key=m.id)
            table.refresh()
        except Exception as e:
            self.notify(str(e), severity="error")

    @work
    async def action_load_model(self) -> None:
        model_id = self._focused_model_id()
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
        model_id = self._focused_model_id()
        if not model_id:
            self.app.notify("Select a model row first", severity="warning", timeout=4.0)
            return
        confirmed = await self.app.push_screen_wait(
            ConfirmModal(f"Unload '{model_id}'?", "Unload Model")
        )
        if confirmed:
            self._do_unload(model_id)

    @work
    async def action_download_model(self) -> None:
        # Pre-fill with focused model ID if available; user can edit it
        prefill = self._focused_model_id() or ""
        model_id = await self.app.push_screen_wait(DownloadModelModal(prefill=prefill))
        if model_id:
            self._do_download(model_id)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _focused_model_id(self) -> str | None:
        table = self.query_one("#models-table", DataTable)
        if table.cursor_row < 0:
            return None
        try:
            cell = table.get_cell_at((table.cursor_row, 0))
            return str(cell)
        except (IndexError, KeyError):
            return None

    @work
    async def _do_load(self, request) -> None:
        client = self.app.server_registry.active_client
        if not client:
            return
        try:
            self.notify(f"Loading {request.model}…")
            await client.load_model(request)
            # Persist load params so modal pre-fills next time
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
            models = await client.list_models()
            instance_id = next(
                (m.instance_id for m in models if m.id == model_id and m.instance_id),
                None,
            )
            if not instance_id:
                self.notify(f"No loaded instance found for {model_id}", severity="warning")
                return
            await client.unload_model(instance_id)
            self.notify(f"Unloaded {model_id}", severity="information")
            self.action_refresh()
        except Exception as e:
            self.notify(str(e), severity="error")

    @work
    async def _do_download(self, model_id: str) -> None:
        client = self.app.server_registry.active_client
        if not client:
            return
        try:
            await client.download_model(model_id)
            self.notify(f"Download started: {model_id}")
            self._start_download_poll(client, model_id)
        except Exception as e:
            # Friendly message when the download endpoint is unsupported
            err_str = str(e)
            if "404" in err_str or "Not Found" in err_str:
                self.notify(
                    "Download not supported on this server version. "
                    "Use the LM Studio desktop app to download models.",
                    severity="warning",
                    timeout=8.0,
                )
            else:
                self.notify(err_str, severity="error")

    def _start_download_poll(self, client, model_id: str = "") -> None:
        self._dl_client = client
        self._dl_model_id = model_id
        dl_bar = self.query_one("#dl-bar")
        dl_bar.remove_class("-hidden")
        self.query_one("#dl-label", Label).update(f"Downloading: {model_id}  ")
        self.query_one("#dl-progress", ProgressBar).update(progress=0)
        if self._dl_timer:
            self._dl_timer.stop()
        self._dl_timer = self.set_interval(2.0, self._poll_download)

    def _cancel_download(self) -> None:
        if self._dl_timer:
            self._dl_timer.stop()
            self._dl_timer = None
        self.query_one("#dl-bar").add_class("-hidden")
        self.notify("Download cancelled", severity="warning")

    @work(exclusive=True)
    async def _poll_download(self) -> None:
        client = self._dl_client or self.app.server_registry.active_client
        if not client:
            return
        status = await client.get_download_status()
        if not status:
            # Status endpoint not available — stop polling, hide bar
            if self._dl_timer:
                self._dl_timer.stop()
                self._dl_timer = None
            self.query_one("#dl-bar").add_class("-hidden")
            return
        name = status.model or getattr(self, "_dl_model_id", "")
        self.query_one("#dl-label", Label).update(f"Downloading: {name}  ")
        pct = int(status.progress * 100)
        self.query_one("#dl-progress", ProgressBar).update(progress=pct)
        if status.status == "complete":
            if self._dl_timer:
                self._dl_timer.stop()
                self._dl_timer = None
            self.query_one("#dl-bar").add_class("-hidden")
            self.notify(f"Downloaded {name}", severity="information")
            self.action_refresh()
        elif status.status == "error":
            if self._dl_timer:
                self._dl_timer.stop()
                self._dl_timer = None
            self.query_one("#dl-bar").add_class("-hidden")
            self.notify(f"Download failed: {name}", severity="error")
