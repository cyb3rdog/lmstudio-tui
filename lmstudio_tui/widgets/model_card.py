from __future__ import annotations

import re

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Label, ProgressBar, Sparkline, Static

from ..api.models import ModelInfo
from ..utils.formatting import format_ctx, format_ms, format_tps


def _safe_id(raw: str) -> str:
    """Convert a model ID to a CSS-safe identifier."""
    return re.sub(r"[^a-zA-Z0-9_-]", "-", raw)


class ModelCard(Widget):
    """Rich card showing details + live metrics for a single loaded model."""

    def __init__(self, model: ModelInfo, **kwargs) -> None:
        super().__init__(**kwargs)
        self._model = model
        self._sid = _safe_id(model.id)
        # Store widget references to avoid fragile ID-based queries
        self._tps_spark: Sparkline | None = None
        self._ttft_spark: Sparkline | None = None
        self._tps_label: Static | None = None
        self._ttft_label: Static | None = None
        self._vram_bar: ProgressBar | None = None
        self._vram_label: Label | None = None

    def compose(self) -> ComposeResult:
        m = self._model
        quant = m.quantization or "—"
        ctx = format_ctx(m.max_context_length or m.context_length)
        layers = f"{m.gpu_layers}L GPU" if m.gpu_layers else "CPU"
        kv = m.kv_cache_type or "—"

        # Inference parameters line (only show fields that are set)
        params_parts = []
        if m.temperature is not None:
            params_parts.append(f"Temp: {m.temperature:.2f}")
        if m.top_p is not None:
            params_parts.append(f"Top-p: {m.top_p:.2f}")
        if m.repeat_penalty is not None:
            params_parts.append(f"Rep: {m.repeat_penalty:.2f}")
        params_str = "  |  ".join(params_parts) if params_parts else None

        yield Label(f"  {m.id}", classes="card-title")
        yield Label(
            f"  Quant: {quant}  |  Ctx: {ctx}  |  {layers}  |  KV: {kv}",
            classes="card-meta",
        )
        if params_str:
            yield Label(f"  {params_str}", classes="card-params")

        self._tps_label = Static("  TPS  —")
        self._ttft_label = Static("  TTFT —")
        self._tps_spark = Sparkline(data=[])
        self._ttft_spark = Sparkline(data=[])
        self._vram_bar = ProgressBar(total=100, show_eta=False)
        self._vram_label = Label("  VRAM: n/a")

        yield self._tps_label
        yield self._tps_spark
        yield self._ttft_label
        yield self._ttft_spark
        yield self._vram_bar
        yield self._vram_label

    def update_metrics(
        self,
        tps_series: list[float],
        ttft_series: list[float],
        vram_used_gb: float | None = None,
        vram_total_gb: float | None = None,
    ) -> None:
        if self._tps_spark and tps_series:
            self._tps_spark.data = tps_series
            if self._tps_label:
                self._tps_label.update(f"  TPS  {format_tps(tps_series[-1])}")

        if self._ttft_spark and ttft_series:
            self._ttft_spark.data = ttft_series
            if self._ttft_label:
                self._ttft_label.update(f"  TTFT {format_ms(ttft_series[-1])}")

        if vram_used_gb is not None and vram_total_gb and self._vram_bar and self._vram_label:
            pct = min(100, int((vram_used_gb / vram_total_gb) * 100))
            self._vram_bar.update(progress=pct)
            self._vram_label.update(f"  VRAM: {vram_used_gb:.1f} / {vram_total_gb:.1f} GB")

    def refresh_model(self, model: ModelInfo) -> None:
        """Update stored model data (e.g. after reload with new params)."""
        self._model = model
