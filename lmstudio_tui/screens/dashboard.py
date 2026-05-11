from __future__ import annotations

import asyncio

from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Label, Static
from textual import work

from ..api.models import ModelInfo
from ..state.server_registry import ConnectionState
from ..utils.formatting import format_ctx
from ..widgets.model_card import ModelCard


class Dashboard(Widget):
    """Dashboard view: server status + loaded model cards + unloaded model list."""

    class QuickLoad(Message):
        """Emitted when the user wants to quick-load a model from the unloaded bar."""
        def __init__(self, model_id: str) -> None:
            super().__init__()
            self.model_id = model_id

    class NavigateToModels(Message):
        """Emitted when user clicks Manage in the unloaded bar."""

    DEFAULT_CSS = """
    Dashboard {
        width: 1fr;
        height: 1fr;
    }
    Dashboard #server-bar {
        height: 3;
        padding: 0 1;
        background: $surface-darken-1;
        border-bottom: solid $primary-darken-3;
    }
    Dashboard #models-scroll {
        height: 1fr;
    }
    Dashboard #unloaded-panel {
        height: auto;
        min-height: 3;
        max-height: 8;
        padding: 0 1 1 1;
        background: $surface-darken-2;
        border-top: solid $primary-darken-3;
    }
    Dashboard #unloaded-panel.-hidden { display: none; }
    Dashboard #unloaded-header {
        height: 2;
        padding: 0;
        align: left middle;
    }
    Dashboard #unloaded-title {
        color: $text-muted;
        width: 1fr;
        text-style: bold;
        height: 2;
        content-align: left middle;
    }
    Dashboard #btn-manage-models {
        width: auto;
        height: 1;
        margin: 0;
        min-width: 12;
    }
    Dashboard #unloaded-chips {
        height: auto;
        flex-wrap: wrap;
    }
    Dashboard .unloaded-chip {
        width: auto;
        height: 1;
        margin: 0 1 0 0;
        background: $surface;
        color: $text-muted;
        border: none;
        padding: 0 1;
        min-width: 4;
    }
    Dashboard .unloaded-chip:hover {
        background: $primary-darken-2;
        color: $text;
    }
    Dashboard #empty-placeholder {
        height: 1fr;
        align: center middle;
        color: $text-muted;
        text-style: italic;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("  Connecting…", id="server-bar")
        with ScrollableContainer(id="models-scroll"):
            yield Vertical(id="model-cards")
        yield Static("[dim]No models loaded[/dim]", id="empty-placeholder")
        with Vertical(id="unloaded-panel", classes="-hidden"):
            with Horizontal(id="unloaded-header"):
                yield Static("  Unloaded models", id="unloaded-title")
                yield Button("→ Manage", id="btn-manage-models", variant="default")
            yield Horizontal(id="unloaded-chips")

    def on_mount(self) -> None:
        self._refresh_timer = self.set_interval(
            self.app.config.ui.poll_interval_s,
            self._refresh,
        )
        self._refresh()

    def on_resize(self) -> None:
        self._update_server_bar()

    def _update_server_bar(self) -> None:
        conn = self.app.server_registry.active_connection
        if not conn:
            return
        server_bar = self.query_one("#server-bar", Static)
        endpoint = conn.config.endpoint
        if self.size.width < 60 and len(endpoint) > 30:
            endpoint = endpoint[:27] + "…"
        if conn.state == ConnectionState.CONNECTED and conn.client:
            ping_str = f"{conn.ping_ms:.0f}ms" if conn.ping_ms else "—"
            server_bar.update(
                f"  [bold]{endpoint}[/bold]   "
                f"[green]● Connected[/green]   {ping_str}"
            )
        elif conn.state == ConnectionState.CONNECTING:
            server_bar.update(f"  [yellow]◌ Connecting…[/yellow]")
        else:
            server_bar.update(f"  [red]✗ {conn.last_error or 'unreachable'}[/red]")

    def on_unmount(self) -> None:
        self._refresh_timer.stop()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-manage-models":
            self.post_message(self.NavigateToModels())
        elif event.button.has_class("unloaded-chip"):
            self.post_message(self.QuickLoad(str(event.button.label)))

    @work(exclusive=True)
    async def _refresh(self) -> None:
        conn = self.app.server_registry.active_connection

        if not conn or conn.state != ConnectionState.CONNECTED:
            for _ in range(20):
                await asyncio.sleep(0.25)
                conn = self.app.server_registry.active_connection
                if conn and conn.state == ConnectionState.CONNECTED:
                    break

        if not conn:
            return

        server_bar = self.query_one("#server-bar", Static)

        if conn.state == ConnectionState.CONNECTED and conn.client:
            try:
                models = await conn.client.list_models()
                conn.models = models
                ping_str = f"{conn.ping_ms:.0f}ms" if conn.ping_ms else "—"
                server_bar.update(
                    f"  [bold]{conn.config.endpoint}[/bold]   "
                    f"[green]● Connected[/green]   {ping_str}"
                )
                self._render_models(models)
            except Exception as e:
                server_bar.update(f"  [red]Error: {e}[/red]")
        elif conn.state == ConnectionState.CONNECTING:
            server_bar.update(f"  [yellow]◌ Connecting to {conn.config.endpoint}…[/yellow]")
        else:
            err = conn.last_error or "unreachable"
            server_bar.update(
                f"  {conn.config.endpoint}   [red]✗ {err}[/red]"
            )

    def _render_models(self, models: list[ModelInfo]) -> None:
        loaded = [m for m in models if m.is_loaded]
        unloaded = [m for m in models if not m.is_loaded]

        container = self.query_one("#model-cards", Vertical)
        existing: dict[str, ModelCard] = {
            card._model.id: card for card in container.query(ModelCard)
        }
        loaded_ids = {m.id for m in loaded}

        for mid, card in list(existing.items()):
            if mid not in loaded_ids:
                card.remove()

        for model in loaded:
            if model.id in existing:
                existing[model.id].refresh_model(model)
            else:
                container.mount(ModelCard(model))

        store = self.app.metrics_store
        active = self.app.server_registry.active_name
        for card in container.query(ModelCard):
            tps = store.get_tps_series(active, card._model.id)
            ttft = store.get_ttft_series(active, card._model.id)
            card.update_metrics(tps, ttft)

        placeholder = self.query_one("#empty-placeholder", Static)
        placeholder.display = len(container.query(ModelCard)) == 0

        # Unloaded panel — show chips for each unloaded model
        panel = self.query_one("#unloaded-panel")
        chips_row = self.query_one("#unloaded-chips", Horizontal)

        if unloaded:
            panel.remove_class("-hidden")
            title = self.query_one("#unloaded-title", Static)
            title.update(f"  Unloaded ({len(unloaded)})")

            # Reconcile chips: remove old, add new
            existing_chips = {btn.id for btn in chips_row.query(Button)}
            new_ids = {f"chip-{m.id.replace('/', '-').replace('.', '-').replace(':', '-')}" for m in unloaded}

            for btn in list(chips_row.query(Button)):
                if btn.id not in new_ids:
                    btn.remove()

            existing_chip_ids = {btn.id for btn in chips_row.query(Button)}
            for m in unloaded:
                chip_id = f"chip-{m.id.replace('/', '-').replace('.', '-').replace(':', '-')}"
                if chip_id not in existing_chip_ids:
                    chips_row.mount(Button(m.id, id=chip_id, classes="unloaded-chip"))
        else:
            panel.add_class("-hidden")
            for btn in list(chips_row.query(Button)):
                btn.remove()
