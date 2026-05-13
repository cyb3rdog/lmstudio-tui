# LM Studio TUI - Roadmap

## Current Status: ✅ Phase 1–5 Complete — v0.2 Preview

**v0.2 adds: configurable HTTP timeout, configurable metrics window, server switching UI, central threshold constant. All items completed 2026-05-13.**

---

## ✅ Phase 5B: Mobile UX Redesign — COMPLETE (v0.2)

| Feature | Status | Notes |
|---------|--------|-------|
| UX-1 | ✅ | NARROW_SCREEN_THRESHOLD = 65 centralised in `constants.py` |
| UX-2 | ✅ | All screens reference constant (chat.py, benchmark_runner.py, settings.py) |
| UX-3 | ✅ | MetricsStore window configurable via Settings + config.toml |
| UX-4 | ✅ | Benchmark runner buttons visible at all resolutions |
| UX-5 | ✅ | Portrait/landscape auto-detection via `self.size.width < NARROW_SCREEN_THRESHOLD` |

---

## ✅ Phase 6: Configurable HTTP Timeout — COMPLETE (v0.2)

| Feature | Status | Notes |
|---------|--------|-------|
| TO-1 | ✅ | `ServerConfig.timeout_s` field (default 900s, range 10–3600) |
| TO-2 | ✅ | `LMStudioClient` uses `config.timeout_s` for httpx.AsyncClient |
| TO-3 | ✅ | Editable per-server in Settings → Edit (ServerFormModal) |
| TO-4 | ✅ | Editable for active server in Settings → App Preferences |
| TO-5 | ✅ | Config.toml serialised with `timeout_s` field |

---

## ✅ Phase 7: Server Switching UI — COMPLETE (v0.2)

| Feature | Status | Notes |
|---------|--------|-------|
| SW-1 | ✅ | "Set Active" button in Settings below server list |
| SW-2 | ✅ | Active server marked `★` in ListView |
| SW-3 | ✅ | `ServerRegistry.active_name` setter wired to UI |
| SW-4 | ✅ | All screens operate on active server |

---

## Phase 8: Multi-Server Simultaneous Monitoring (Planned)

| Feature | Priority | Description |
|---------|----------|-------------|
| Multi-1 | MEDIUM | Server selector widget in sidebar — switch without going to Settings |
| Multi-2 | MEDIUM | Live Monitor shows metrics from all configured servers |
| Multi-3 | MEDIUM | Dashboard shows status bar for all servers |

---

## Phase 9: Advanced Benchmarking (Planned)

| Feature | Priority | Description |
|---------|----------|-------------|
| Bench-adv-1 | LOW | Multi-turn tool benchmark (send tool result back, evaluate final answer) |
| Bench-adv-2 | LOW | Distractor tools (measure hallucination / wrong-tool rate) |
| Bench-adv-3 | LOW | Concurrency sweep (plot aggregate TPS vs. parallel slots 1–16) |
| Bench-adv-4 | LOW | Context length sweep (TPS vs. context for same model) |

---

## Phase 10: Dead Code Cleanup (Planned for v0.2)

| Feature | Status | Notes |
|---------|--------|-------|
| DC-1 | LOW | Remove or document `widgets/comparison_chart.py` (never imported) |
| DC-2 | LOW | Remove or document `widgets/status_badge.py` (never imported) |
| DC-3 | LOW | Remove or document `api/sse.py` (never imported, endpoint returns 404) |
| DC-4 | LOW | Remove `scripts/benchmark-lmstudio.bak` backup |

---

## Quick Reference

### Working Features
- ✅ Dashboard — server status bar, model cards with sparklines
- ✅ Models — table (with Quant + Ctx columns), load/unload, Downloads screen
- ✅ Chat — streaming chat, model selector, history, Stop/Clear, feeds Live Monitor
- ✅ Monitor — TPS/TTFT sparklines, recent requests table (populated by Chat + Benchmark)
- ✅ Benchmark — model SelectionList, mode checkboxes, unload-all flow, load time, tool calling, parallel, export
- ✅ Settings — server CRUD, Set Active, connection test, prefs (poll/timeout/window/export)
- ✅ Portrait/landscape responsive; all toolbars stack on narrow screens (< 65 cols)
- ✅ Keyboard shortcuts overlay (`?`); number keys 1–7 always navigate
- ✅ **212 tests passing**

### New in v0.2
- Configurable HTTP timeout per server (default 900s — large model JIT-load safe)
- Configurable metrics ring-buffer window (default 120, adjustable 10–500)
- Centralised `NARROW_SCREEN_THRESHOLD = 65` constant
- Server switching UI — "Set Active" in Settings, `★` marker in server list
- `MetricsStore.all_recent(limit=0)` fix — returns `[]` instead of crash

### Known Limitations
- TTFT is wall-clock only (LM Studio's `stats` field is always empty)
- `reasoning_tokens` is a streaming chunk-count proxy
- Download cancel is best-effort — no cancel API in LM Studio v1
- SSE log stream not implemented (endpoint returns 404 on current server)
- VRAM values show `—` (LM Studio v1 API does not expose per-model VRAM)
- `prompt_tokens` for streaming chat responses is `0`