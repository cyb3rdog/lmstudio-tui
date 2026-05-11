# LM Studio TUI - Roadmap

## Current Status: ✅ Phase 1, 2, 3A, 3B & 3C Complete

All planned features have been implemented. Core UX, chat, benchmark, and test suite are production-ready.

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

## ✅ Test Suite — COMPLETE (93 tests, 0 failures)

| File | Coverage |
|------|----------|
| `tests/test_api_models.py` | ModelsResponse, ModelInfo, field validators |
| `tests/test_api_client.py` | ping, list_models, load_model, _extract_metrics |
| `tests/test_benchmark_analysis.py` | percentile, IQR outliers, analyze, detect_winners |
| `tests/test_agentic_benchmark.py` | Tool suite, scoring, agentic analyze |

---

## Phase 4: Advanced Features (Optional)

| Feature | Priority | Description |
|---------|----------|-------------|
| SSE-1 | MEDIUM | SSE log stream via `/api/v1/chat` native streaming events |
| Multi-1 | LOW | Server switching UI (server selector widget in sidebar) |
| Multi-2 | LOW | Multi-server simultaneous monitoring |
| Bench-adv-1 | LOW | Multi-turn tool benchmark (send tool result back, evaluate final answer) |
| Bench-adv-2 | LOW | Distractor tools (measure hallucination / wrong-tool rate) |
| Bench-adv-3 | LOW | Concurrency sweep (plot aggregate TPS vs. parallel slots 1–16) |

---

## Quick Reference

### Working Features
- ✅ Dashboard — server status bar, model cards with sparklines
- ✅ Models — table, load/unload/download, responsive toolbar (stacks on mobile)
- ✅ Chat — streaming chat, model selector, history, Stop/Clear, feeds Live Monitor
- ✅ Monitor — TPS/TTFT sparklines, recent requests table (populated by Chat + Benchmark)
- ✅ Benchmark — model SelectionList, mode checkboxes, unload-all flow, load time, tool calling, parallel, export
- ✅ Settings — server config, connection test, prefs
- ✅ Portrait/landscape responsive; all toolbars stack on narrow screens
- ✅ Keyboard shortcuts overlay (`?`); number keys 1-6 always navigate
- ✅ 93 tests passing

### Known Limitations
- TTFT is wall-clock only (LM Studio's `stats` field is always empty)
- `reasoning_tokens` is a streaming chunk-count proxy (no real count from `/v1/chat/completions`)
- Download progress endpoint returns 404 on some server versions
- SSE log stream not implemented (endpoint varies by server version)
- VRAM values show "—" (LM Studio v1 API does not expose per-model VRAM usage)