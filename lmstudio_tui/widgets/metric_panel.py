from __future__ import annotations

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label, ProgressBar, Sparkline, Static

from ..utils.formatting import format_ms, format_tps


class MetricPanel(Widget):
    """TPS sparkline + TTFT sparkline + VRAM progress bar for Live Monitor."""

    DEFAULT_CSS = """
    MetricPanel {
        border: round $primary-darken-2;
        padding: 0 1;
        margin-bottom: 1;
        height: auto;
    }
    MetricPanel .mp-title { text-style: bold; }
    MetricPanel Sparkline { height: 3; width: 1fr; }
    MetricPanel ProgressBar { width: 1fr; }
    """

    tps_data: reactive[list[float]] = reactive(list)
    ttft_data: reactive[list[float]] = reactive(list)
    vram_pct: reactive[float] = reactive(0.0)

    def __init__(self, model_id: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._model_id = model_id

    def compose(self) -> ComposeResult:
        yield Label(f"  {self._model_id}", classes="mp-title")
        yield Static("  TPS  —", id="mp-tps-val")
        yield Sparkline(data=[], id="mp-tps-spark")
        yield Static("  TTFT —", id="mp-ttft-val")
        yield Sparkline(data=[], id="mp-ttft-spark")
        yield Label("  VRAM", id="mp-vram-lbl")
        yield ProgressBar(total=100, id="mp-vram-bar", show_eta=False)

    def watch_tps_data(self, data: list[float]) -> None:
        try:
            self.query_one("#mp-tps-spark", Sparkline).data = data
            val = format_tps(data[-1]) if data else "—"
            self.query_one("#mp-tps-val", Static).update(f"  TPS  {val}")
        except Exception:
            pass

    def watch_ttft_data(self, data: list[float]) -> None:
        try:
            self.query_one("#mp-ttft-spark", Sparkline).data = data
            val = format_ms(data[-1]) if data else "—"
            self.query_one("#mp-ttft-val", Static).update(f"  TTFT {val}")
        except Exception:
            pass

    def watch_vram_pct(self, pct: float) -> None:
        try:
            self.query_one("#mp-vram-bar", ProgressBar).update(progress=pct)
        except Exception:
            pass

    def set_vram(self, used_gb: float, total_gb: float) -> None:
        if total_gb > 0:
            self.vram_pct = min(100.0, (used_gb / total_gb) * 100)
            try:
                self.query_one("#mp-vram-lbl", Label).update(
                    f"  VRAM  {used_gb:.1f} / {total_gb:.1f} GB"
                )
            except Exception:
                pass
