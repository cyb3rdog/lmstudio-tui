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
        # Widget refs stored to avoid duplicate-ID issues across multiple panels
        self._tps_val: Static | None = None
        self._tps_spark: Sparkline | None = None
        self._ttft_val: Static | None = None
        self._ttft_spark: Sparkline | None = None
        self._vram_lbl: Label | None = None
        self._vram_bar: ProgressBar | None = None

    def compose(self) -> ComposeResult:
        yield Label(f"  {self._model_id}", classes="mp-title")

        self._tps_val = Static("  TPS  —")
        self._tps_spark = Sparkline(data=[])
        self._ttft_val = Static("  TTFT —")
        self._ttft_spark = Sparkline(data=[])
        self._vram_lbl = Label("  VRAM")
        self._vram_bar = ProgressBar(total=100, show_eta=False)

        yield self._tps_val
        yield self._tps_spark
        yield self._ttft_val
        yield self._ttft_spark
        yield self._vram_lbl
        yield self._vram_bar

    def watch_tps_data(self, data: list[float]) -> None:
        if self._tps_spark is not None:
            self._tps_spark.data = data
        if self._tps_val is not None:
            val = format_tps(data[-1]) if data else "—"
            self._tps_val.update(f"  TPS  {val}")

    def watch_ttft_data(self, data: list[float]) -> None:
        if self._ttft_spark is not None:
            self._ttft_spark.data = data
        if self._ttft_val is not None:
            val = format_ms(data[-1]) if data else "—"
            self._ttft_val.update(f"  TTFT {val}")

    def watch_vram_pct(self, pct: float) -> None:
        if self._vram_bar is not None:
            self._vram_bar.update(progress=pct)

    def set_vram(self, used_gb: float, total_gb: float) -> None:
        if total_gb > 0:
            self.vram_pct = min(100.0, (used_gb / total_gb) * 100)
            if self._vram_lbl is not None:
                self._vram_lbl.update(f"  VRAM  {used_gb:.1f} / {total_gb:.1f} GB")
