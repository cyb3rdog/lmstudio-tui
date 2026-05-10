from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Button, DataTable, Label, ProgressBar, Static
from textual import work

from ..utils.formatting import format_ctx
from .modals.confirm_dialog import ConfirmModal
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
    }
    ModelManager #dl-bar.-hidden { display: none; }
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

    def on_mount(self) -> None:
        table = self.query_one("#models-table", DataTable)
        table.add_columns("Model", "Status", "Quant", "Ctx", "VRAM")
        self._dl_timer = None
        self.action_refresh()

    def on_unmount(self) -> None:
        if self._dl_timer:
            self._dl_timer.stop()

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

    # ── actions (all decorated with @work so push_screen_wait is safe) ────────

    @work(exclusive=True)
    async def action_refresh(self) -> None:
        client = self.app.server_registry.active_client
        if not client:
            return
        try:
            models = await client.list_models()
            table = self.query_one("#models-table", DataTable)
            table.clear()
            for m in models:
                status = "LOADED" if m.is_loaded else "—"
                quant = m.quantization or "—"
                ctx = format_ctx(m.max_context_length or m.context_length)
                vram = "—"
                table.add_row(m.id, status, quant, ctx, vram, key=m.id)
        except Exception as e:
            self.notify(str(e), severity="error")

    @work
    async def action_load_model(self) -> None:
        model_id = self._focused_model_id()
        if not model_id:
            self.notify("Select a model row first", severity="warning")
            return
        result = await self.app.push_screen_wait(ModelLoadModal(model_id))
        if result:
            self._do_load(result)

    @work
    async def action_unload_model(self) -> None:
        model_id = self._focused_model_id()
        if not model_id:
            self.notify("Select a model row first", severity="warning")
            return
        confirmed = await self.app.push_screen_wait(
            ConfirmModal(f"Unload '{model_id}'?", "Unload Model")
        )
        if confirmed:
            self._do_unload(model_id)

    @work
    async def action_download_model(self) -> None:
        model_id = self._focused_model_id()
        if not model_id:
            self.notify("Select a model row first", severity="warning")
            return
        self._do_download(model_id)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _focused_model_id(self) -> str | None:
        table = self.query_one("#models-table", DataTable)
        if table.cursor_row < 0:
            return None
        try:
            cell = table.get_cell_at((table.cursor_row, 0))
            return str(cell)
        except Exception:
            return None

    @work
    async def _do_load(self, request) -> None:
        client = self.app.server_registry.active_client
        if not client:
            return
        try:
            self.notify(f"Loading {request.model}…")
            await client.load_model(request)
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
            self._start_download_poll()
        except Exception as e:
            self.notify(str(e), severity="error")

    def _start_download_poll(self) -> None:
        dl_bar = self.query_one("#dl-bar")
        dl_bar.remove_class("-hidden")
        if self._dl_timer:
            self._dl_timer.stop()
        self._dl_timer = self.set_interval(2.0, self._poll_download)

    @work(exclusive=True)
    async def _poll_download(self) -> None:
        client = self.app.server_registry.active_client
        if not client:
            return
        status = await client.get_download_status()
        if not status:
            return
        self.query_one("#dl-label", Label).update(f"Downloading: {status.model}  ")
        pct = int(status.progress * 100)
        self.query_one("#dl-progress", ProgressBar).update(progress=pct)
        if status.status == "complete":
            if self._dl_timer:
                self._dl_timer.stop()
            self.query_one("#dl-bar").add_class("-hidden")
            self.notify(f"Downloaded {status.model}", severity="information")
            self.action_refresh()
