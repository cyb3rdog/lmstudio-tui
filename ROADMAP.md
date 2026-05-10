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
| Nav-4 | ✅ | Escape always returns to nav (smart toggle behavior) |
| Mobile-1 | ✅ | Sidebar auto-collapse < 70 cols; `Ctrl+B` toggle |
| Mobile-2 | ✅ | Mini-header shows server state + screen name |
| Mobile-3 | ✅ | Number keys 1-6 work regardless of sidebar state |

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

---

## ✅ Phase 3C: Comprehensive Benchmarking — COMPLETE

| Feature | Status | Notes |
|---------|--------|-------|
| Bench-1 | ✅ | Load time tracking via `/api/v1/models/load` + wall-clock fallback |
| Bench-2 | ✅ | Winner detection (`detect_winners()` marks best per metric) |
| Bench-3 | ✅ | TPOT metric (time per output token via streaming) |
| Bench-4 | ✅ | Reasoning token counting (`reasoning_content` field) |
| Bench-5 | ✅ | Multi-mode via checkboxes (Throughput, Tool, Parallel) |

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
| SSE-1 | MEDIUM | SSE log stream endpoint (if server exposes) |
| Multi-1 | LOW | Server switching UI (server selector widget) |
| Multi-2 | LOW | Multi-server simultaneous monitoring |

---

## Quick Reference

### Working Features
- ✅ Dashboard — server status bar, model cards
- ✅ Models — 12-column table, load/unload/download
- ✅ Chat — streaming chat, model selector, history, Stop/Clear
- ✅ Monitor — TPS/TTFT sparklines, VRAM, requests table
- ✅ Benchmark — multi-model, IQR outlier removal, winner detection
- ✅ Settings — server config, connection test
- ✅ Export — JSON, CSV, Markdown formats
- ✅ 93 tests passing

### Known Limitations
- TTFT wall-clock only (server's `stats` field empty)
- Download progress 404 on some server versions
- No SSE log stream (endpoint varies by server)