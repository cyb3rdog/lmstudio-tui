from __future__ import annotations

import time

from textual.app import ComposeResult
from textual.containers import ScrollableContainer, Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import DataTable, Label, Static
from textual import work

from ..utils.formatting import format_ms, format_tps
from ..widgets.metric_panel import MetricPanel


class LiveMonitor(Widget):
    DEFAULT_CSS = """
    LiveMonitor {
        width: 1fr;
        height: 1fr;
    }
    LiveMonitor #toolbar {
        height: 3;
        padding: 0 1;
        background: $surface-darken-1;
        border-bottom: solid $primary-darken-3;
    }
    LiveMonitor #panels-scroll { height: 1fr; }
    LiveMonitor #recent-table { height: 12; }
    LiveMonitor #recent-label {
        padding: 0 1;
        color: $text-muted;
        height: 1;
    }
    """

    BINDINGS = [("p", "toggle_pause", "Pause/Resume")]

    paused: reactive[bool] = reactive(False)

    def compose(self) -> ComposeResult:
        yield Static("  Live Monitor   [dim][P] Pause[/dim]", id="toolbar")
        with ScrollableContainer(id="panels-scroll"):
            yield Vertical(id="metric-panels")
        yield Label("  Recent Requests", id="recent-label")
        yield DataTable(id="recent-table", cursor_type="none", show_header=True)

    def on_mount(self) -> None:
        table = self.query_one("#recent-table", DataTable)
        table.add_columns("Time", "Model", "TPS", "TTFT", "In / Out tokens")
        self._timer = self.set_interval(1.0, self._refresh)

    def on_unmount(self) -> None:
        self._timer.stop()

    def action_toggle_pause(self) -> None:
        self.paused = not self.paused

    def watch_paused(self, paused: bool) -> None:
        if paused:
            self._timer.pause()
            self.query_one("#toolbar", Static).update("  Live Monitor   [yellow]⏸ Paused — [P] Resume[/yellow]")
        else:
            self._timer.resume()
            self.query_one("#toolbar", Static).update("  Live Monitor   [dim][P] Pause[/dim]")

    @work(exclusive=True)
    async def _refresh(self) -> None:
        client = self.app.server_registry.active_client
        if not client:
            return
        try:
            models = await client.list_models()
        except Exception:
            return

        loaded = [m for m in models if m.is_loaded]
        store = self.app.metrics_store
        active = self.app.server_registry.active_name

        panels_container = self.query_one("#metric-panels", Vertical)
        existing = {p._model_id for p in panels_container.query(MetricPanel)}
        loaded_ids = {m.id for m in loaded}

        for panel in list(panels_container.query(MetricPanel)):
            if panel._model_id not in loaded_ids:
                panel.remove()

        for model in loaded:
            if model.id not in existing:
                panels_container.mount(MetricPanel(model.id, id=f"mp-{model.id.replace('/', '-').replace('.', '-')}"))

        for panel in panels_container.query(MetricPanel):
            mid = panel._model_id
            panel.tps_data = store.get_tps_series(active, mid)
            panel.ttft_data = store.get_ttft_series(active, mid)

        # Update recent requests table
        table = self.query_one("#recent-table", DataTable)
        table.clear()
        recent = store.all_recent(active, limit=20)
        for s in recent:
            t = time.strftime("%H:%M:%S", time.localtime(s.timestamp))
            table.add_row(
                t,
                s.model_id[:28],
                format_tps(s.tokens_per_second),
                format_ms(s.time_to_first_token_ms),
                f"{s.prompt_tokens} / {s.completion_tokens}",
            )
