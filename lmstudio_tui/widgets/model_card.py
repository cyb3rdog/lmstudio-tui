from __future__ import annotations

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label, ProgressBar, Sparkline, Static

from ..api.models import ModelInfo
from ..utils.formatting import format_ctx, format_ms, format_tps


class ModelCard(Widget):
    """Rich card showing details + live metrics for a single loaded model."""

    DEFAULT_CSS = """
    ModelCard {
        border: round $primary-darken-2;
        padding: 0 1;
        margin-bottom: 1;
        height: auto;
    }
    ModelCard .card-title {
        text-style: bold;
        color: $text;
    }
    ModelCard .card-meta {
        color: $text-muted;
    }
    ModelCard .metric-row {
        height: 3;
    }
    ModelCard Sparkline {
        height: 3;
        width: 1fr;
    }
    ModelCard ProgressBar {
        width: 1fr;
    }
    """

    tps_data: reactive[list[float]] = reactive(list, recompose=False)
    ttft_data: reactive[list[float]] = reactive(list, recompose=False)

    def __init__(self, model: ModelInfo, **kwargs) -> None:
        super().__init__(**kwargs)
        self._model = model

    def compose(self) -> ComposeResult:
        m = self._model
        quant = m.quantization or "—"
        ctx = format_ctx(m.max_context_length or m.context_length)
        layers = f"{m.gpu_layers} layers" if m.gpu_layers is not None else "CPU"
        kv = m.kv_cache_type or "—"

        yield Label(f"  {m.id}", classes="card-title")
        yield Label(
            f"  Quant: {quant}  |  Ctx: {ctx}  |  Offload: {layers}  |  KV cache: {kv}",
            classes="card-meta",
        )
        yield Static(f"  TPS  ", id="tps-label")
        yield Sparkline(data=[], id=f"tps-spark-{m.id}")
        yield Static(f"  TTFT ", id="ttft-label")
        yield Sparkline(data=[], id=f"ttft-spark-{m.id}")
        yield ProgressBar(total=100, id=f"vram-bar-{m.id}", show_eta=False)
        yield Label("  VRAM: —", id=f"vram-label-{m.id}")

    def update_metrics(
        self,
        tps_series: list[float],
        ttft_series: list[float],
        vram_used_gb: float | None = None,
        vram_total_gb: float | None = None,
    ) -> None:
        mid = self._model.id
        try:
            spark_tps = self.query_one(f"#tps-spark-{mid}", Sparkline)
            spark_tps.data = tps_series
            if tps_series:
                self.query_one("#tps-label", Static).update(
                    f"  TPS  {format_tps(tps_series[-1])}"
                )
        except Exception:
            pass

        try:
            spark_ttft = self.query_one(f"#ttft-spark-{mid}", Sparkline)
            spark_ttft.data = ttft_series
            if ttft_series:
                self.query_one("#ttft-label", Static).update(
                    f"  TTFT {format_ms(ttft_series[-1])}"
                )
        except Exception:
            pass

        if vram_used_gb is not None and vram_total_gb:
            pct = min(100, int((vram_used_gb / vram_total_gb) * 100))
            try:
                self.query_one(f"#vram-bar-{mid}", ProgressBar).update(progress=pct)
                self.query_one(f"#vram-label-{mid}", Label).update(
                    f"  VRAM: {vram_used_gb:.1f} / {vram_total_gb:.1f} GB"
                )
            except Exception:
                pass
