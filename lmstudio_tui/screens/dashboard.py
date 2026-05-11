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
    """Dashboard view: server status + loaded model cards + unloaded summary."""

    class NavigateToModels(Message):
        """Emitted when user clicks '→ Manage Models' in the unloaded panel."""

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
    Dashboard #empty-placeholder {
        height: 1fr;
        align: center middle;
        color: $text-muted;
        text-style: italic;
    }
    Dashboard #unloaded-panel {
        height: auto;
        min-height: 3;
        max-height: 6;
        padding: 0 1 0 1;
        background: $surface-darken-2;
        border-top: solid $primary-darken-3;
    }
    Dashboard #unloaded-panel.-hidden { display: none; }
    Dashboard #unloaded-row {
        height: 3;
        align: left middle;
    }
    Dashboard #unloaded-title {
        color: $text-muted;
        width: 1fr;
        height: 3;
        content-align: left middle;
    }
    Dashboard #btn-manage-models {
        width: auto;
        height: 1;
        min-width: 14;
    }
    Dashboard #unloaded-names {
        height: auto;
        color: $text-muted;
        padding: 0 0 1 0;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("  Connecting…", id="server-bar")
        with ScrollableContainer(id="models-scroll"):
            yield Vertical(id="model-cards")
        yield Static("[dim]No models loaded[/dim]", id="empty-placeholder")
        with Vertical(id="unloaded-panel", classes="-hidden"):
            with Horizontal(id="unloaded-row"):
                yield Static("  Unloaded: —", id="unloaded-title")
                yield Button("→ Manage Models", id="btn-manage-models", variant="default")
            yield Static("", id="unloaded-names")

    def on_mount(self) -> None:
        self._refresh_timer = self.set_interval(
            self.app.config.ui.poll_interval_s,
            self._refresh,
        )
        self._refresh()

    def on_show(self) -> None:
        self._refresh_timer.resume()
        self._refresh()

    def on_hide(self) -> None:
        self._refresh_timer.pause()

    def on_unmount(self) -> None:
        self._refresh_timer.stop()

    def on_resize(self) -> None:
        self._update_server_bar()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-manage-models":
            self.post_message(self.NavigateToModels())

    def _update_server_bar(self) -> None:
        conn = self.app.server_registry.active_connection
        if not conn:
            return
        server_bar = self.query_one("#server-bar", Static)
        w = self.size.width
        # Reserve space: "  " prefix + "   ● Connected   XXXms" = ~24 chars
        max_ep = max(12, w - 26)
        endpoint = conn.config.endpoint
        if len(endpoint) > max_ep:
            endpoint = endpoint[:max_ep - 1] + "…"
        if conn.state == ConnectionState.CONNECTED and conn.client:
            ping_str = f"{conn.ping_ms:.0f}ms" if conn.ping_ms else "—"
            if w < 50:
                server_bar.update(f"  [green]●[/green] {endpoint}  {ping_str}")
            else:
                server_bar.update(
                    f"  [bold]{endpoint}[/bold]   [green]● Connected[/green]   {ping_str}"
                )
        elif conn.state == ConnectionState.CONNECTING:
            server_bar.update(f"  [yellow]◌ Connecting…[/yellow]")
        else:
            server_bar.update(f"  [red]✗ {conn.last_error or 'unreachable'}[/red]")

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
                self._update_server_bar()
                await self._render_models(models)
            except Exception as e:
                server_bar.update(f"  [red]Error: {e}[/red]")
        elif conn.state == ConnectionState.CONNECTING:
            server_bar.update(f"  [yellow]◌ Connecting…[/yellow]")
        else:
            err = conn.last_error or "unreachable"
            server_bar.update(f"  [red]✗ {err}[/red]")

    async def _render_models(self, models: list[ModelInfo]) -> None:
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
                await card.remove()

        # Add cards for newly loaded models; refresh existing ones
        for model in loaded:
            if model.id in existing:
                existing[model.id].refresh_model(model)
            else:
                await container.mount(ModelCard(model))

        # Push latest metrics into cards
        store = self.app.metrics_store
        active = self.app.server_registry.active_name
        for card in container.query(ModelCard):
            tps = store.get_tps_series(active, card._model.id)
            ttft = store.get_ttft_series(active, card._model.id)
            card.update_metrics(tps, ttft)

        # Empty-state placeholder
        placeholder = self.query_one("#empty-placeholder", Static)
        placeholder.display = len(loaded) == 0

        # Unloaded panel — compact summary: count + truncated name list + Manage button
        panel = self.query_one("#unloaded-panel")
        if unloaded:
            panel.remove_class("-hidden")
            self.query_one("#unloaded-title", Static).update(
                f"  [dim]Unloaded ({len(unloaded)})[/dim]"
            )
            # Show up to 5 names; truncate to fit narrow screens
            max_width = max(self.size.width - 4, 20)
            names_line = "  " + "  ·  ".join(m.id for m in unloaded[:5])
            if len(unloaded) > 5:
                names_line += f"  … +{len(unloaded) - 5} more"
            if len(names_line) > max_width:
                names_line = names_line[:max_width - 1] + "…"
            self.query_one("#unloaded-names", Static).update(f"[dim]{names_line}[/dim]")
        else:
            panel.add_class("-hidden")
