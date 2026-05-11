# LM Studio TUI - Roadmap

## Current Status: ✅ Phase 1, 2, 3A, 3B & 3C Complete

All critical, high, and medium-priority work done. Core UX, chat, agentic
benchmarking, and full test suite implemented.

---

## ✅ Phase 3A: Core UX Foundation — COMPLETE

| Feature | Status | Notes |
|---------|--------|-------|
| Nav-1: Tab cycles sidebar ↔ content | ✅ | Native Textual Tab order |
| Nav-2: Focus indicators on all widgets | ✅ | CSS `:focus` rings on Button, DataTable, Select, Input, SelectionList |
| Nav-3: Keyboard shortcuts overlay (`?`) | ✅ | `ShortcutsModal` via `?` key |
| Nav-4: Escape → toggle sidebar (smart) | ✅ | First Escape: focus nav. Second Escape while nav focused: collapse sidebar |
| Nav-5: Ctrl+B toggle | ✅ | Toggles collapse/expand; auto-focuses content when collapsing |
| Nav-6: After selection auto-collapse | ✅ | Portrait (<70 cols): Enter on nav item collapses sidebar |
| Mobile-1: Portrait collapsible sidebar | ✅ | Auto-collapse < 70 cols; `Ctrl+B` / Escape toggle |
| Mobile-2: Mini-header with screen name | ✅ | 3-tier responsive: < 50, < 70, ≥ 70 cols; updates on resize |
| Mobile-3: Number keys 1-6 always work | ✅ | Regardless of sidebar state |
| Mobile-4: All toolbars stack on narrow screens | ✅ | ModelManager, Chat, Settings, Benchmark all stack < ~60 cols |

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
| Chat-7: MetricsStore integration | ✅ | Each chat turn records TPS/TTFT/tokens to Live Monitor |

---

## ✅ Phase 3C: Agentic Benchmarking — COMPLETE

| Feature | Status | Notes |
|---------|--------|-------|
| Bench-1: Streaming TTFT/TPOT | ✅ | `agentic_inference()` — wall-clock to first SSE token |
| Bench-2: TPS with streaming fallback | ✅ | Uses `usage` field; falls back to content-chunk count |
| Bench-3: Model SelectionList | ✅ | All server models (loaded + not loaded), ●/○ status |
| Bench-4: Mode checkboxes | ✅ | Throughput, Tool Calling, Parallel — independent multi-select |
| Bench-5: "Full (all)" shortcut | ✅ | Button checks all mode checkboxes |
| Bench-6: Benchmark flow | ✅ | Unload all → per model: load → run modes → unload → next |
| Bench-7: Load time capture | ✅ | Uses `load_time_seconds` from LM Studio response (authoritative) |
| Bench-8: JIT load detection | ✅ | `was_jit=True` when model was not loaded before benchmark |
| Bench-9: Tool calling evaluation | ✅ | 4 synthetic tools, 10 test cases, name + arg fuzzy scoring |
| Bench-10: Reasoning token tracking | ✅ | Counts `reasoning_content` delta chunks (proxy — see limitations) |
| Bench-11: Parallel benchmarking | ✅ | `asyncio.Semaphore(N)` slots, aggregate TPS |
| Bench-12: Winner detection | ✅ | ★ best TPS / TTFT / tool accuracy / load time |
| Bench-13: Export JSON/CSV/Markdown | ✅ | Mode-specific tables with winner markers |
| Bench-14: Real-time table updates | ✅ | Per-sample rows appear as inference completes |
| Bench-15: Summary panel | ✅ | Per-model aggregate stats with ★ |

---

## ✅ Tests — COMPLETE (93 tests, 0 failures)

| File | Coverage |
|------|----------|
| `tests/test_api_models.py` | `ModelsResponse.from_raw`, `ModelInfo.is_loaded`, field validators |
| `tests/test_api_client.py` | `ping`, `list_models`, `load_model`, `_extract_metrics`, error handling |
| `tests/test_benchmark_analysis.py` | `_percentile`, `_remove_iqr_outliers`, `analyze` |
| `tests/test_agentic_benchmark.py` | Tool suite, `_score_tool_args`, agentic analysis, winner detection |

---

## Phase 4: Advanced Features

| Feature | Priority | Description |
|---------|----------|-------------|
| SSE-1 | MEDIUM | Log stream (SSE endpoint via `/api/v1/chat` native streaming events) |
| Multi-1 | LOW | Server switching UI (server selector widget in sidebar) |
| Multi-2 | LOW | Multi-server simultaneous monitoring |
| Bench-adv-1 | LOW | Multi-turn tool benchmark (send tool result back, evaluate final answer) |
| Bench-adv-2 | LOW | Distractor tools (measure hallucination rate) |
| Bench-adv-3 | LOW | Concurrency sweep (plot aggregate TPS vs. parallel slots 1–16) |

---

## Quick Reference

### Working Features
- ✅ Dashboard — server status bar, model cards with sparklines
- ✅ Models — table, load/unload/download, progress bar, stacked toolbar on mobile
- ✅ Chat — streaming chat, model selector, history, Stop/Clear, feeds Live Monitor
- ✅ Monitor — TPS/TTFT sparklines, VRAM, recent requests table (populated by Chat + Benchmark)
- ✅ Benchmark — model SelectionList, mode checkboxes, unload-all flow, load time, tool calling, parallel, export
- ✅ Settings — server list, add/edit/remove, connection test, prefs
- ✅ Portrait/landscape responsive (sidebar auto-collapse, all toolbars stack)
- ✅ Keyboard shortcuts overlay (`?`)
- ✅ Number keys 1-6 always navigate
- ✅ Escape toggles sidebar (smart: second press collapses)
- ✅ Test suite: 93 tests covering API, models, benchmark analysis, agentic metrics

### Known Limitations
- TTFT is wall-clock only (LM Studio's `stats` field is always empty)
- `reasoning_tokens` is a streaming-chunk count proxy — LM Studio's `/v1/chat/completions` rolls reasoning into `completion_tokens` without a separate details field
- Download progress endpoint returns 404 on some server versions
- SSE log stream not implemented (endpoint varies by server version)
- VRAM values always show "—" (LM Studio v1 API does not expose per-model VRAM usage)
