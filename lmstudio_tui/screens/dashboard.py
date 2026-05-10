from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import ScrollableContainer, Vertical
from textual.widget import Widget
from textual.widgets import Label, Static
from textual import work

from ..api.models import ModelInfo
from ..state.server_registry import ConnectionState
from ..utils.formatting import format_ctx
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
        height: auto;
        min-height: 2;
        padding: 0 1;
        background: $surface-darken-1;
        border-top: solid $primary-darken-3;
        color: $text-muted;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("  Connecting…", id="server-bar")
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

        # Remove cards for models no longer loaded
        for mid, card in list(existing.items()):
            if mid not in loaded_ids:
                card.remove()

        # Add cards for newly loaded models; refresh model data on existing ones
        for model in loaded:
            if model.id in existing:
                existing[model.id].refresh_model(model)
            else:
                container.mount(ModelCard(model))

        # Push latest metrics into cards
        store = self.app.metrics_store
        active = self.app.server_registry.active_name
        for card in container.query(ModelCard):
            tps = store.get_tps_series(active, card._model.id)
            ttft = store.get_ttft_series(active, card._model.id)
            card.update_metrics(tps, ttft)

        # Unloaded bar — wrap long lists across two lines on narrow screens
        unloaded_bar = self.query_one("#unloaded-bar", Static)
        if unloaded:
            visible = unloaded[:10]
            rest = len(unloaded) - len(visible)
            names = "  |  ".join(m.id for m in visible)
            suffix = f"  … +{rest} more" if rest > 0 else ""
            unloaded_bar.update(f"  Unloaded ({len(unloaded)}): {names}{suffix}")
        else:
            unloaded_bar.update("")
