# LM Studio TUI - Roadmap

## Current Status: ✅ Phase 1, 2 & 3A/3B Complete

All critical, high, and medium-priority issues resolved. Core UX, chat, and test suite implemented.

---

## ✅ Phase 3A: Core UX Foundation — COMPLETE

| Feature | Status | Notes |
|---------|--------|-------|
| Nav-1: Tab cycles sidebar ↔ content | ✅ | Native Textual Tab order; Escape returns to nav |
| Nav-2: Focus indicators on all widgets | ✅ | CSS `:focus` rings on Button, DataTable, Select, ListView |
| Nav-3: Keyboard shortcuts overlay (`?`) | ✅ | `ShortcutsModal` via `?` key |
| Nav-4: Consistent Escape → nav | ✅ | `action_focus_nav` always returns to sidebar |
| Mobile-1: Portrait collapsible sidebar | ✅ | Auto-collapse < 70 cols; `Ctrl+B` toggle |
| Mobile-2: Mini-header with screen name | ✅ | Updates on every screen switch |
| Mobile-3: Number keys 1-6 always work | ✅ | Regardless of sidebar state |

---

## ✅ Phase 3B: Interactive Chat — COMPLETE

| Feature | Status | Notes |
|---------|--------|-------|
| Chat-1: Chat screen with input/output | ✅ | `screens/chat.py` |
| Chat-2: Streaming response display | ✅ | Live token-by-token preview via `chat_completion_stream` |
| Chat-3: Model selector | ✅ | Select widget, re-populated on screen show |
| Chat-4: Conversation history | ✅ | Full history sent on each request; RichLog display |
| Chat-5: Stop streaming | ✅ | Abort via Stop button (`asyncio.Event`) |
| Chat-6: Clear conversation | ✅ | `Ctrl+L` |

---

## ✅ Tests — COMPLETE (58 tests, 0 failures)

| File | Coverage |
|------|----------|
| `tests/test_api_models.py` | `ModelsResponse.from_raw`, `ModelInfo.is_loaded`, field validators |
| `tests/test_api_client.py` | `ping`, `list_models`, `load_model`, `_extract_metrics`, error handling |
| `tests/test_benchmark_analysis.py` | `_percentile`, `_remove_iqr_outliers`, `analyze` |

---

## Phase 3C: Comprehensive Benchmarking

**Goal:** Full feature parity with benchmark-lmstudio.py

| Feature | Priority | Description |
|---------|----------|-------------|
| Bench-1 | HIGH | Load time tracking (JIT detection via polling) |
| Bench-2 | HIGH | Winner detection per metric category |
| Bench-3 | MEDIUM | TPOT metric (time per output token) |
| Bench-4 | MEDIUM | Reasoning token counting (`reasoning_content`) |
| Bench-5 | MEDIUM | Full/quick/tool benchmark mode selector |

---

## Phase 4: Advanced Features

| Feature | Priority | Description |
|---------|----------|-------------|
| SSE-1 | MEDIUM | Log stream (SSE endpoint, if server exposes one) |
| Multi-1 | LOW | Server switching UI (server selector widget) |
| Multi-2 | LOW | Multi-server simultaneous monitoring |

---

## Quick Reference

### Working Features
- ✅ Dashboard — server status bar, model cards with sparklines
- ✅ Models — 12-column table, load/unload/download, progress bar
- ✅ Chat — streaming chat, model selector, history, Stop/Clear
- ✅ Monitor — TPS/TTFT sparklines, VRAM, recent requests table
- ✅ Benchmark — multi-model, IQR outlier removal, CSV/JSON/MD export
- ✅ Settings — server list, add/edit/remove, connection test, prefs
- ✅ Portrait/landscape responsive (sidebar auto-collapse)
- ✅ Keyboard shortcuts overlay (`?`)
- ✅ Number keys 1-6 always navigate
- ✅ Test suite: 58 tests covering API, models, and benchmark analysis

### Known Limitations
- TTFT is wall-clock only (LM Studio's `stats` field is always empty)
- Download progress endpoint returns 404 on some server versions
- SSE log stream not implemented (endpoint varies by server)
- No load time tracking in benchmark
