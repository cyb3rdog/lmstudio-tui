# LM Studio TUI - Roadmap

## Current Status: ✅ Phase 1, 2, 3A, 3B, 3C, 4A & Post-Audit Fixes Complete

**Post-Audit: 32 issues resolved (7 critical, 5 memory/leak, 4 race, 6 perf, 10 UX). 212 tests passing.**

---

## ✅ Phase 3A: Core UX Foundation — COMPLETE

| Feature | Status | Notes |
|---------|--------|-------|
| Nav-1 | ✅ | Tab cycles sidebar ↔ content via Textual DOM order |
| Nav-2 | ✅ | Focus rings on Button, DataTable, Select, ListView |
| Nav-3 | ✅ | ShortcutsModal via `?` key binding |
| Nav-4 | ✅ | Escape: focus nav; second Escape while nav focused collapses sidebar |
| Nav-5 | ✅ | Ctrl+B toggles collapse/expand; auto-focuses content when collapsing |
| Nav-6 | ✅ | Portrait (<70 cols): Enter on nav item auto-collapses sidebar |
| Mobile-1 | ✅ | Sidebar auto-collapse < 70 cols; Ctrl+B / Escape toggle |
| Mobile-2 | ✅ | Mini-header: 3-tier responsive (< 50, < 70, ≥ 70 cols); updates on resize |
| Mobile-3 | ✅ | Number keys 1-6 work regardless of sidebar state |
| Mobile-4 | ✅ | All toolbars stack vertically on narrow screens (< ~60 cols) |

---

## ✅ Phase 3B: Interactive Chat — COMPLETE

| Feature | Status | Notes |
|---------|--------|-------|
| Chat-1 | ✅ | `screens/chat.py` with streaming via `agentic_inference` |
| Chat-2 | ✅ | Live token preview updates during streaming |
| Chat-3 | ✅ | Model selector (Select widget, re-populated on show) |
| Chat-4 | ✅ | Full conversation history sent on each request |
| Chat-5 | ✅ | Stop button with `asyncio.Event` abort |
| Chat-6 | ✅ | Clear via `Ctrl+L` |
| Chat-7 | ✅ | Each turn records TPS/TTFT/tokens to MetricsStore → Live Monitor |

---

## ✅ Phase 3C: Comprehensive Benchmarking — COMPLETE

| Feature | Status | Notes |
|---------|--------|-------|
| Bench-1 | ✅ | Load time via `load_time_seconds` from LM Studio response (authoritative) |
| Bench-2 | ✅ | Winner detection (`detect_winners()` marks best per metric category) |
| Bench-3 | ✅ | TPOT metric (time per output token, streaming wall-clock) |
| Bench-4 | ✅ | Reasoning token chunk count (`reasoning_content` delta proxy) |
| Bench-5 | ✅ | Mode checkboxes: Throughput, Tool Calling, Parallel + "Full (all)" |
| Bench-6 | ✅ | Model SelectionList: all server models, ●/○ status, Select/Deselect All |
| Bench-7 | ✅ | Benchmark flow: unload all → load → run modes → unload → next model |
| Bench-8 | ✅ | JIT detection: `was_jit=True` when model was not loaded pre-benchmark |
| Bench-9 | ✅ | Tool calling: 4 synthetic tools, 10 test cases, name + arg fuzzy scoring |
| Bench-10 | ✅ | Parallel mode: `asyncio.Semaphore(N)` slots, aggregate TPS |
| Bench-11 | ✅ | Export: JSON/CSV/Markdown with mode-specific tables and ★ winners |
| Bench-12 | ✅ | Real-time per-sample rows + per-model summary panel |

---

## ✅ Test Suite — COMPLETE (212 tests, 0 failures)

| File | Tests | Coverage |
|------|-------|---------|
| `tests/test_api_models.py` | 12 | ModelsResponse, ModelInfo, field validators |
| `tests/test_api_client.py` | 18 | ping, list_models, load_model, _extract_metrics |
| `tests/test_benchmark_analysis.py` | 20 | percentile, IQR outliers, analyze, detect_winners |
| `tests/test_agentic_benchmark.py` | 29 | Tool suite, scoring, agentic analyze |
| `tests/test_hub_api.py` | 19 | HubModel formatting, search_hub URL params, error handling |
| `tests/test_server_registry.py` | 18 | ServerRegistry lifecycle, add/remove, active switching |
| `tests/test_config.py` | 13 | Config defaults, save/load roundtrip, ServerConfig |
| `tests/test_audit_fixes.py` | 83 | MetricsStore edge cases, tool suite schema, CompletionMetrics, ChatMessage |

---

## ✅ Phase 4A: Download Manager — COMPLETE

| Feature | Status | Notes |
|---------|--------|-------|
| DM-1 | ✅ | `api/hub.py` — HuggingFace search (`GET /api/models?filter=gguf`) |
| DM-2 | ✅ | `screens/download_manager.py` — HF browse, download start/poll/cancel (self-contained) |
| DM-3 | ✅ | Default view: top GGUF models by downloads (no query required) |
| DM-4 | ✅ | Row-key tracking prevents truncated-ID bugs on narrow terminals |
| DM-5 | ✅ | Fallback: paste full `author/model-GGUF` ID directly into search input |
| DM-6 | ✅ | 19 tests in `tests/test_hub_api.py` |

---

## Phase 4B: Advanced Features (Optional)

| Feature | Priority | Description |
|---------|----------|-------------|
| SSE-1 | MEDIUM | SSE log stream via `/api/v1/chat` native streaming events (stub exists in `api/sse.py`, endpoint returns 404 on current server) |
| Multi-1 | LOW | Server switching UI (server selector widget in sidebar) |
| Multi-2 | LOW | Multi-server simultaneous monitoring |
| Bench-adv-1 | LOW | Multi-turn tool benchmark (send tool result back, evaluate final answer) |
| Bench-adv-2 | LOW | Distractor tools (measure hallucination / wrong-tool rate) |
| Bench-adv-3 | LOW | Concurrency sweep (plot aggregate TPS vs. parallel slots 1–16) |

---

## Phase 5: Download Manager — Rename (2026-05-11)

| Feature | Status | Notes |
|---------|--------|-------|
| AR-1 | ✅ | Clean separation: ModelManager (screen 2) = load/unload only; Downloads (screen 6) = browse + download |
| AR-2 | ✅ | Removed download logic from ModelManager (poll, cancel, _dl_* vars) |
| AR-3 | ✅ | Download Manager (`screens/download_manager.py`) is self-contained: browse, start, poll, cancel |
| AR-4 | ✅ | Download progress bar lives in Download Manager, not ModelManager |
| AR-5 | ✅ | ModelManager toolbar: Load/Unload/Downloads [D]/Refresh |
| AR-6 | ✅ | Deleted `screens/hub.py` shim — DownloadManager imported directly from `screens/download_manager.py` |
| AR-7 | ✅ | Consistent naming: screen "Downloads", class `DownloadManager`, file `download_manager.py` |

---

## Phase 5B: Mobile UX Redesign (Planned)

| Feature | Priority | Description |
|---------|----------|-------------|
| UX-1 | HIGH | Revisit portrait UX flows (≤70 cols) — navigation, toolbars, table display |
| UX-2 | MEDIUM | Revisit landscape UX flows (≥70 cols) — benchmark runner, live monitor |
| UX-3 | HIGH | Compact mode as default UX — optimize for constrained hardware (Pi Zero 2W) |
| UX-4 | MEDIUM | Benchmark runner buttons visible at all resolutions |
| UX-5 | LOW | Portrait/landscape auto-detection and adaptive layout |

---

## Quick Reference

### Working Features
- ✅ Dashboard — server status bar, model cards with sparklines
- ✅ Models — table (with Quant + Ctx columns), load/unload, Downloads screen (browse/search/download GGUF from HuggingFace), responsive toolbar
- ✅ Chat — streaming chat, model selector, history, Stop/Clear, feeds Live Monitor
- ✅ Monitor — TPS/TTFT sparklines, recent requests table (populated by Chat + Benchmark), DOM rebuilds throttled to new data only
- ✅ Benchmark — model SelectionList, mode checkboxes, context length param, unload-all flow, load time, tool calling (per-tool filtered), parallel, export
- ✅ Settings — server config, connection test, prefs with poll interval guard (≥0.5s)
- ✅ Portrait/landscape responsive; all toolbars stack on narrow screens
- ✅ Keyboard shortcuts overlay (`?`); number keys 1-7 always navigate
- ✅ 212 tests passing

### Known Limitations
- TTFT is wall-clock only (LM Studio's `stats` field is always empty)
- `reasoning_tokens` is a streaming chunk-count proxy (no real count from `/v1/chat/completions`)
- Download cancel is best-effort — LM Studio v1 does not expose a cancel API endpoint
- SSE log stream not implemented (endpoint varies by server version)
- VRAM values show "—" (LM Studio v1 API does not expose per-model VRAM usage)
- `prompt_tokens` for streaming chat responses is `0` (LM Studio does not send `usage` in streaming chunks)
