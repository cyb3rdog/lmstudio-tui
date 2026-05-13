# Changelog

## [Unreleased]

### Maintenance — v0.2.0 Release Prep

- **Version**: Bumped `pyproject.toml` to `0.2.0`, aligned all docs (README, CHANGELOG, ROADMAP)
- **Version export**: `lmstudio_tui.__version__` now exposed via `importlib.metadata`
- **Dead code documented**: `ComparisonChart`, `StatusBadge`, `SSEClient` now carry `@planned` docstrings (Phase 10 / Phase 8)
- **Navigation consistency**: `push_screen()` usage confirmed as modal-only; `action_goto()` used for screen navigation throughout
- **README accuracy**: Removed non-existent keyboard shortcuts (`S`/`X` for benchmark, `D` for downloads, `Ctrl+B`/`Escape` for sidebar); corrected benchmark buttons to `▶ Start`/`■ Stop`
- **docs/ removed**: Orphan `docs/` directory with empty `archive/` removed
- **Contributing guide expanded**: Added code style tools, architecture overview, PR checklist, release process
- **pyproject.toml enhanced**: Added `readme`, `keywords`, `classifiers` for better PyPI display

### HTTP Timeout — Configurable
- **ServerConfig** now has a `timeout_s` field (default: 900s) instead of hardcoded 120s
- **LMStudioClient** uses `config.timeout_s` for all HTTP requests — large models (70B+ Q4+) can now JIT-load without premature timeouts
- Per-server timeout editable in Settings → App Preferences (or per-server via Edit)
- `DEFAULT_REQUEST_TIMEOUT_S` centralised in `constants.py`

### Screen Threshold — Centralised
- `NARROW_SCREEN_THRESHOLD = 65` in `constants.py` — single constant, all screens reference it
- Updated: `chat.py`, `benchmark_runner.py`, `settings.py`
- CSS comment updated: "width < 60" → "NARROW_SCREEN_THRESHOLD (65)"

### MetricsWindow — Configurable
- **MetricsStore** now accepts `window` constructor argument (default: 120) instead of hardcoded class constant
- **AppConfig** gains `metrics_window` field (default: 120, range 10–500)
- Configurable in Settings → App Preferences
- Live-adjustable without restart (ring buffer reconfigured in-place)

### Server Switching — Available in Settings
- Settings screen now has a **"Set Active"** button below the server list
- Highlights the active server with `★` in the list view
- Active server shown in server list with `[bold yellow]★` prefix

### Settings Screen — Expanded Preferences
- Added **Request Timeout** field (seconds) — per-active-server setting
- Added **Metrics History** field (samples per model)
- Sections isolated with CSS (poll, timeout, window, export) for clean narrow-screen layout
- Save button at bottom of prefs panel, styled full-width

### Bug Fixes
- `MetricsStore.all_recent(limit=0)` now returns `[]` instead of crashing
- `ServerConfig` timeout clamps to 10–3600s range at load and in Settings form
- `app.tcss` updated: `#set-active-row` button full-width, sections stacked on narrow screens

### Architecture
- New `constants.py` — shared constants (`NARROW_SCREEN_THRESHOLD`, `DEFAULT_REQUEST_TIMEOUT_S`, `METRICS_WINDOW`, `MIN_POLL_INTERVAL_S`)
- `metrics_store.py` removed class-level `WINDOW` constant (now instance-only via constructor)
- Config load/save now handles `timeout_s` and `metrics_window` fields

---

## [0.1.0] - Initial Release

### Features
- Dashboard with server status and model cards
- Model Manager with load/unload/download
- Model Hub browser (HuggingFace GGUF search)
- Streaming Chat interface
- Benchmark Runner (throughput, tool calling, parallel modes)
- Live Monitor with TPS/TTFT sparklines
- Settings with server configuration
- Responsive layout (portrait/landscape)
- Keyboard shortcuts overlay (`?`)

### Test Coverage
- 212 tests passing