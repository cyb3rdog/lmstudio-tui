from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Label, ProgressBar, Static
from textual import work

from ..api.hub import HubModel, search_hub


class DownloadManager(Widget):
    """Browse HuggingFace Hub for GGUF models and manage downloads.

    Responsibilities:
    - Search and browse models from HuggingFace
    - Start downloads on the LM Studio server
    - Track download progress (poll-based)
    - Cancel in-progress downloads

    NOTE: This screen handles downloads. ModelManager (screen 2) handles
    loading and unloading already-downloaded models.
    """

    class DownloadRequested(Message):
        """Emitted when the user confirms a download (for app-level routing)."""
        def __init__(self, model_id: str) -> None:
            super().__init__()
            self.model_id = model_id

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._selected_model_id: str | None = None
        self._dl_timer = None
        self._dl_client = None
        self._dl_model_id = ""
        self._dl_cancelled = False

    def compose(self) -> ComposeResult:
        with Horizontal(id="search-bar"):
            yield Input(
                placeholder="Search GGUF models… (e.g. llama, mistral, qwen) or paste a full HF model ID",
                id="search-input",
            )
            yield Button("Search", id="btn-search", variant="primary")
        yield Static("Loading popular GGUF models…", id="status-bar")
        yield DataTable(id="results-table", cursor_type="row", zebra_stripes=True)
        with Horizontal(id="action-bar"):
            yield Static("No model selected.", id="selected-label")
            yield Button("↓ Download to LM Studio", id="btn-download", variant="primary")
        with Horizontal(id="dl-bar", classes="-hidden"):
            yield Label("Downloading: ", id="dl-label")
            yield ProgressBar(id="dl-progress", total=100, show_eta=False)
            yield Button("✕ Cancel", id="btn-dl-cancel", variant="error")

    def on_mount(self) -> None:
        table = self.query_one("#results-table", DataTable)
        table.add_columns("Model ID", "Downloads", "♥ Likes")

    def on_show(self) -> None:
        if self.query_one("#results-table", DataTable).row_count == 0:
            self._do_search("")

    def on_hide(self) -> None:
        """Stop download polling timer when screen is hidden."""
        if self._dl_timer:
            self._dl_timer.stop()
            self._dl_timer = None

    def on_unmount(self) -> None:
        if self._dl_timer:
            self._dl_timer.stop()

    # ── events ────────────────────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "btn-search":
                self._do_search(self.query_one("#search-input", Input).value)
            case "btn-download":
                self._confirm_download()
            case "btn-dl-cancel":
                self._cancel_download()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "search-input":
            self._do_search(event.value)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key and event.row_key.value is not None:
            self._selected_model_id = str(event.row_key.value)
            try:
                self.query_one("#selected-label", Static).update(
                    f"[dim]Selected:[/dim]  {self._selected_model_id}"
                )
            except Exception:
                pass

    # ── search ────────────────────────────────────────────────────────────────

    @work(exclusive=True)
    async def _do_search(self, query: str) -> None:
        try:
            self.query_one("#status-bar", Static).update("[dim]Searching…[/dim]")
            self.query_one("#btn-search", Button).disabled = True
        except Exception:
            return

        results: list[HubModel] = []
        error: str | None = None
        try:
            results = await search_hub(query.strip())
        except Exception as e:
            error = str(e)

        try:
            self.query_one("#btn-search", Button).disabled = False
        except Exception:
            pass

        if error:
            try:
                self.query_one("#status-bar", Static).update(
                    f"[red]Search failed:[/red] {error}"
                )
            except Exception:
                pass
            return

        self._selected_model_id = None
        try:
            table = self.query_one("#results-table", DataTable)
            table.clear()
            for m in results:
                table.add_row(m.id, m.downloads_fmt, m.likes_fmt, key=m.id)
            q_label = f'"{query.strip()}"' if query.strip() else "popular models"
            self.query_one("#status-bar", Static).update(
                f"[dim]{len(results)} results for {q_label}[/dim]"
            )
            self.query_one("#selected-label", Static).update("No model selected.")
        except Exception:
            pass

    # ── download ──────────────────────────────────────────────────────────────

    def _confirm_download(self) -> None:
        model_id = self._selected_model_id
        if not model_id:
            text = self.query_one("#search-input", Input).value.strip()
            if "/" in text:
                model_id = text
            else:
                self.notify(
                    "Select a model from the list, or paste a full author/model-GGUF ID",
                    severity="warning",
                )
                return
        self._start_download(model_id)

    @work
    async def _start_download(self, model_id: str) -> None:
        client = self.app.server_registry.active_client
        if not client:
            self.notify("Not connected to a server", severity="warning")
            return
        try:
            await client.download_model(model_id)
            self.notify(f"Download started: {model_id}")
            self._show_download_bar(model_id)
        except Exception as e:
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

    def _show_download_bar(self, model_id: str) -> None:
        self._dl_client = self.app.server_registry.active_client
        self._dl_model_id = model_id
        self._dl_cancelled = False
        dl_bar = self.query_one("#dl-bar")
        dl_bar.remove_class("-hidden")
        self.query_one("#dl-label", Label).update(f"Downloading: {model_id}  ")
        self.query_one("#dl-progress", ProgressBar).update(progress=0)
        if self._dl_timer:
            self._dl_timer.stop()
        self._dl_timer = self.set_interval(2.0, self._poll_download)

    def _cancel_download(self) -> None:
        self._dl_cancelled = True
        if self._dl_timer:
            self._dl_timer.stop()
            self._dl_timer = None
        self.query_one("#dl-bar").add_class("-hidden")
        self.notify("Download cancelled (server may continue downloading)", severity="warning")

    @work(exclusive=True)
    async def _poll_download(self) -> None:
        # Guard: honour cancellation before starting each poll iteration.
        if self._dl_cancelled:
            return
        client = self._dl_client or self.app.server_registry.active_client
        if not client:
            return
        status = await client.get_download_status()
        # Guard: check again after the API call (race with cancel during I/O).
        if self._dl_cancelled:
            return
        if not status:
            self._hide_download_bar()
            return
        name = status.model or self._dl_model_id
        self.query_one("#dl-label", Label).update(f"Downloading: {name}  ")
        self.query_one("#dl-progress", ProgressBar).update(progress=int(status.progress * 100))
        if status.status == "complete":
            self._hide_download_bar()
            self.notify(f"Downloaded {name}", severity="information")
        elif status.status == "error":
            self._hide_download_bar()
            self.notify(f"Download failed: {name}", severity="error")

    def _hide_download_bar(self) -> None:
        if self._dl_timer:
            self._dl_timer.stop()
            self._dl_timer = None
        self._dl_client = None
        try:
            self.query_one("#dl-bar").add_class("-hidden")
        except Exception:
            pass
