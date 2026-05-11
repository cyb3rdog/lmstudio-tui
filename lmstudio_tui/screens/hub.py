from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Static
from textual import work

from ..api.hub import HubModel, search_hub


class ModelHub(Widget):
    """Browse and search HuggingFace Hub for GGUF models.

    Emits DownloadRequested when the user commits a download; the app
    routes that to ModelManager so download progress shows there.
    """

    DEFAULT_CSS = """
    ModelHub {
        width: 1fr;
        height: 1fr;
        layout: vertical;
    }
    ModelHub #search-bar {
        height: 3;
        padding: 0 1;
        background: $surface-darken-1;
        border-bottom: solid $primary-darken-3;
    }
    ModelHub #search-bar Input { width: 1fr; }
    ModelHub #search-bar Button { width: 10; margin-left: 1; }
    ModelHub #status-bar {
        height: 1;
        padding: 0 1;
        color: $text-muted;
        background: $surface-darken-2;
    }
    ModelHub #results-table { height: 1fr; }
    ModelHub #action-bar {
        height: 3;
        padding: 0 1;
        background: $surface-darken-1;
        border-top: solid $primary-darken-3;
    }
    ModelHub #selected-label {
        width: 1fr;
        height: 3;
        content-align: left middle;
        color: $text-muted;
    }
    ModelHub #btn-download { width: auto; }
    """

    class DownloadRequested(Message):
        """Emitted when the user confirms a download."""
        def __init__(self, model_id: str) -> None:
            super().__init__()
            self.model_id = model_id

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._selected_model_id: str | None = None

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

    def on_mount(self) -> None:
        table = self.query_one("#results-table", DataTable)
        table.add_columns("Model ID", "Downloads", "♥ Likes")

    def on_show(self) -> None:
        if self.query_one("#results-table", DataTable).row_count == 0:
            self._do_search("")

    # ── events ────────────────────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "btn-search":
                self._do_search(self.query_one("#search-input", Input).value)
            case "btn-download":
                self._confirm_download()

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

    # ── actions ───────────────────────────────────────────────────────────────

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
        self.post_message(self.DownloadRequested(model_id))

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
