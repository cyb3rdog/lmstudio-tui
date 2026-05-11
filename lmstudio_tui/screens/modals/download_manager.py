from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Input, Label, Static
from textual import work

from ...api.hub import HubModel, search_hub


class DownloadManagerModal(ModalScreen[str | None]):
    """Browse, search, and download GGUF models from HuggingFace Hub.

    Returns the selected model ID string on confirm, None on cancel.
    The caller is responsible for initiating the actual download via the
    LM Studio API.
    """

    DEFAULT_CSS = """
    DownloadManagerModal {
        align: center middle;
    }
    DownloadManagerModal > Vertical {
        width: 92%;
        max-width: 110;
        height: 88%;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }
    DownloadManagerModal #hub-title {
        text-style: bold;
        color: $primary;
        height: 1;
        padding: 0 0 1 0;
    }
    DownloadManagerModal #search-row {
        height: 3;
        margin-bottom: 0;
    }
    DownloadManagerModal #search-row Input {
        width: 1fr;
    }
    DownloadManagerModal #search-row Button {
        width: 10;
        margin-left: 1;
    }
    DownloadManagerModal #hint-label {
        height: 1;
        color: $text-muted;
        padding: 0 0 1 0;
    }
    DownloadManagerModal #status-label {
        height: 1;
        color: $text-muted;
        padding: 0 0 0 0;
    }
    DownloadManagerModal #results-table {
        height: 1fr;
        margin-top: 1;
    }
    DownloadManagerModal #selected-label {
        height: 1;
        color: $text-muted;
        padding: 1 0 0 0;
    }
    DownloadManagerModal #btn-row {
        height: 3;
        margin-top: 1;
        align: left middle;
    }
    DownloadManagerModal #btn-row Button {
        margin: 0 1 0 0;
        width: auto;
    }
    """

    BINDINGS = [("escape", "dismiss_modal", "Close")]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._selected_model_id: str | None = None

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("  Model Hub  —  Browse & Download GGUF Models", id="hub-title")
            with Horizontal(id="search-row"):
                yield Input(
                    placeholder="Search models… (e.g. llama, mistral, qwen) or paste a full HF model ID",
                    id="search-input",
                )
                yield Button("Search", id="btn-search", variant="primary")
            yield Static(
                "[dim]Enter to search · select a row and click Download · or paste a full HF ID and Download directly[/dim]",
                id="hint-label",
            )
            yield Static("Loading popular GGUF models…", id="status-label")
            yield DataTable(id="results-table", cursor_type="row", zebra_stripes=True)
            yield Static("No model selected.", id="selected-label")
            with Horizontal(id="btn-row"):
                yield Button("↓ Download Selected", id="btn-download", variant="primary")
                yield Button("✕ Close", id="btn-close", variant="default")

    def on_mount(self) -> None:
        table = self.query_one("#results-table", DataTable)
        table.add_columns("Model ID", "Downloads", "♥ Likes")
        self.query_one("#search-input", Input).focus()
        self._do_search("")

    # ── events ────────────────────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "btn-search":
                self._do_search(self.query_one("#search-input", Input).value)
            case "btn-download":
                self._confirm_download()
            case "btn-close":
                self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "search-input":
            self._do_search(event.value)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key and event.row_key.value is not None:
            self._selected_model_id = str(event.row_key.value)
            try:
                self.query_one("#selected-label", Static).update(
                    f"[dim]Selected:[/dim]  [bold]{self._selected_model_id}[/bold]"
                )
            except Exception:
                pass

    # ── confirm ───────────────────────────────────────────────────────────────

    def _confirm_download(self) -> None:
        if self._selected_model_id:
            self.dismiss(self._selected_model_id)
            return
        # Fallback: treat search-input text as a direct model ID
        text = self.query_one("#search-input", Input).value.strip()
        if text and "/" in text:
            self.dismiss(text)
        elif text:
            self.notify("Select a model from the list, or enter a full author/model-id", severity="warning")

    # ── search ────────────────────────────────────────────────────────────────

    @work(exclusive=True)
    async def _do_search(self, query: str) -> None:
        try:
            self.query_one("#status-label", Static).update("[dim]Searching…[/dim]")
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
                self.query_one("#status-label", Static).update(
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
            count = len(results)
            q_display = f'"{query}"' if query.strip() else "popular models"
            self.query_one("#status-label", Static).update(
                f"[dim]{count} results for {q_display}[/dim]"
            )
            self.query_one("#selected-label", Static).update("No model selected.")
        except Exception:
            pass

    def action_dismiss_modal(self) -> None:
        self.dismiss(None)
