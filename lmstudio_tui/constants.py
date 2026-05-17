from __future__ import annotations

"""Shared constants across the application."""

# ── Layout thresholds ──────────────────────────────────────────────────────────

# Terminal width (columns) below which screens switch to compact/stacked layout.
# Affects: BenchmarkRunner, Settings, ChatScreen, ModelManager, LiveMonitor.
NARROW_SCREEN_THRESHOLD = 65

# Chat toolbar stacking threshold. Lower than the main threshold because the
# toolbar is narrow by design — it only needs its own stacking transition
# when cols are too tight for the model-select + Send button in one row.
CHAT_TOOLBAR_THRESHOLD = 55

# ── HTTP / API ────────────────────────────────────────────────────────────────

# Default timeout for API requests (load, inference, etc.) in seconds.
# Large models (70B+ Q4+) can take 600–900s to JIT-load. Set high to avoid
# premature disconnects. Can be overridden per-server in config.toml.
DEFAULT_REQUEST_TIMEOUT_S = 900.0

# ── Metrics ───────────────────────────────────────────────────────────────────

# How many metric samples to retain per (server, model_id) in the ring buffer.
# Higher = longer sparkline history, more memory. Constrained hardware (Pi Zero 2W)
# should consider 60; desktop/server can use 120.
METRICS_WINDOW = 120

# ── UI ────────────────────────────────────────────────────────────────────────

# Minimum poll interval (seconds) to prevent CPU saturation on constrained hardware.
MIN_POLL_INTERVAL_S = 0.5