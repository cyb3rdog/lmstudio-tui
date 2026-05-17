from __future__ import annotations

import re
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
    BINDINGS = [("p", "toggle_pause", "Pause/Resume")]

    paused: reactive[bool] = reactive(False)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        # Track last-seen state to avoid rebuilding table when nothing changed.
        self._last_recent_ts: float = 0.0
        self._last_loaded_ids: frozenset[str] = frozenset()

    def compose(self) -> ComposeResult:
        yield Static("  Live Monitor   [dim][P] Pause[/dim]", id="toolbar")
        with ScrollableContainer(id="panels-scroll"):
            yield Vertical(id="metric-panels")
        yield Label("  Recent Requests", id="recent-label")
        yield DataTable(id="recent-table", cursor_type="none", show_header=True)

    def on_mount(self) -> None:
        table = self.query_one("#recent-table", DataTable)
        table.add_columns("Time", "Model", "TPS", "TTFT", "In/Out")
        # Start paused — on_show resumes so it only polls while visible.
        self._timer = self.set_interval(1.0, self._refresh)
        self._timer.pause()

    def on_show(self) -> None:
        if not self.paused:
            self._timer.resume()
        # Reset staleness gates so we get a fresh paint on first show.
        self._last_loaded_ids = frozenset()
        self._last_recent_ts = 0.0
        self._refresh()

    def on_hide(self) -> None:
        self._timer.pause()

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
        # @work catches all exceptions; return early on no-client to avoid DOM queries
        # against potentially unmounted widgets when the server has disconnected.
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
        loaded_ids = frozenset(m.id for m in loaded)

        # ── Metric panels: only modify DOM when set of loaded models changes ──
        if loaded_ids != self._last_loaded_ids:
            self._last_loaded_ids = loaded_ids
            panels_container = self.query_one("#metric-panels", Vertical)
            existing = {p._model_id for p in panels_container.query(MetricPanel)}

            for panel in list(panels_container.query(MetricPanel)):
                if panel._model_id not in loaded_ids:
                    await panel.remove()

            for model in loaded:
                if model.id not in existing:
                    safe_id = re.sub(r"[^a-zA-Z0-9_-]", "-", model.id)
                    await panels_container.mount(MetricPanel(model.id, id=f"mp-{safe_id}"))
        else:
            panels_container = self.query_one("#metric-panels", Vertical)

        # Only push new sparkline data when the sample count actually changed —
        # avoids reactive allocations and Sparkline redraws during idle polling.
        for panel in panels_container.query(MetricPanel):
            mid = panel._model_id
            tps = store.get_tps_series(active, mid)
            ttft = store.get_ttft_series(active, mid)
            if len(tps) != len(panel.tps_data):
                panel.tps_data = tps
            if len(ttft) != len(panel.ttft_data):
                panel.ttft_data = ttft

        # ── Recent requests table: only rebuild when new samples exist ────────
        recent = store.all_recent(active, limit=20)
        newest_ts = recent[0].timestamp if recent else 0.0
        if newest_ts <= self._last_recent_ts:
            return
        self._last_recent_ts = newest_ts

        table = self.query_one("#recent-table", DataTable)
        table.clear()
        w = self.size.width
        mid_len = max(12, min(28, w - 40))
        for s in recent:
            t = time.strftime("%H:%M", time.localtime(s.timestamp))
            table.add_row(
                t,
                s.model_id[:mid_len],
                format_tps(s.tokens_per_second),
                format_ms(s.time_to_first_token_ms),
                f"{s.prompt_tokens}/{s.completion_tokens}",
            )
