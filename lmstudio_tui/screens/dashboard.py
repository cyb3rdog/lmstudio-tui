from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import ScrollableContainer, Vertical
from textual.widget import Widget
from textual.widgets import Label, Static
from textual import work

from ..api.models import ModelInfo, ModelState
from ..state.server_registry import ConnectionState
from ..utils.formatting import format_ctx, format_ms, format_tps
from ..widgets.model_card import ModelCard


class Dashboard(Widget):
    """Dashboard view: server status + loaded model cards."""

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
    Dashboard #unloaded-bar {
        height: 3;
        padding: 0 1;
        background: $surface-darken-1;
        border-top: solid $primary-darken-3;
        color: $text-muted;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("", id="server-bar")
        with ScrollableContainer(id="models-scroll"):
            yield Vertical(id="model-cards")
        yield Static("", id="unloaded-bar")

    def on_mount(self) -> None:
        self._refresh_timer = self.set_interval(
            self.app.config.ui.poll_interval_s,
            self._refresh,
        )
        self._refresh()

    def on_unmount(self) -> None:
        self._refresh_timer.stop()

    @work(exclusive=True)
    async def _refresh(self) -> None:
        conn = self.app.server_registry.active_connection
        if not conn:
            return

        server_bar = self.query_one("#server-bar", Static)

        if conn.state == ConnectionState.CONNECTED and conn.client:
            try:
                models = await conn.client.list_models()
                conn.models = models
                ping_str = f"{conn.ping_ms:.0f}ms" if conn.ping_ms else "—"
                server_bar.update(
                    f"  Server: [bold]{conn.config.endpoint}[/bold]   "
                    f"[green]● Connected[/green]   Ping: {ping_str}"
                )
                self._render_models(models)
            except Exception as e:
                server_bar.update(f"  [red]Error: {e}[/red]")
        elif conn.state == ConnectionState.CONNECTING:
            server_bar.update(f"  [yellow]◌ Connecting to {conn.config.endpoint}…[/yellow]")
        else:
            err = conn.last_error or "unreachable"
            server_bar.update(
                f"  Server: {conn.config.endpoint}   [red]✗ {err}[/red]"
            )

    def _render_models(self, models: list[ModelInfo]) -> None:
        loaded = [m for m in models if m.is_loaded]
        unloaded = [m for m in models if not m.is_loaded]

        container = self.query_one("#model-cards", Vertical)

        existing_ids = {w._model.id for w in container.query(ModelCard)}
        new_ids = {m.id for m in loaded}

        # Remove cards for models no longer loaded
        for card in list(container.query(ModelCard)):
            if card._model.id not in new_ids:
                card.remove()

        # Add cards for newly loaded models
        for model in loaded:
            if model.id not in existing_ids:
                container.mount(ModelCard(model, id=f"card-{model.id.replace('/', '-').replace('.', '-')}"))

        # Update metrics on existing cards
        store = self.app.metrics_store
        active = self.app.server_registry.active_name
        for card in container.query(ModelCard):
            tps = store.get_tps_series(active, card._model.id)
            ttft = store.get_ttft_series(active, card._model.id)
            card.update_metrics(tps, ttft)

        # Update unloaded bar
        unloaded_bar = self.query_one("#unloaded-bar", Static)
        if unloaded:
            names = "  |  ".join(m.id for m in unloaded[:8])
            suffix = f"  … +{len(unloaded) - 8}" if len(unloaded) > 8 else ""
            unloaded_bar.update(f"  Unloaded ({len(unloaded)}): {names}{suffix}")
        else:
            unloaded_bar.update("")
