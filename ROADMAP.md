# LM Studio TUI - Roadmap (Revised)

## Current Status: ✅ Phase 1 & 2 Complete

All critical and high-priority issues have been resolved. The TUI is production-ready for single-server use cases.

---

## Phase 3A: Core UX Foundation (START HERE)

**Goal:** Native TUI navigation and mobile optimization

### Navigation Improvements

| Feature | Priority | Effort | Description |
|---------|----------|--------|-------------|
| Nav-1 | HIGH | 1d | Tab cycles between sidebar and content |
| Nav-2 | HIGH | 1d | Visual focus indicators on all widgets |
| Nav-3 | HIGH | 1d | Keyboard shortcuts overlay (F1 or ?) |
| Nav-4 | HIGH | 1d | Consistent Escape behavior (always to nav) |

### Mobile Portrait Optimization

| Feature | Priority | Effort | Description |
|---------|----------|--------|-------------|
| Mobile-1 | HIGH | 2d | 50×24 terminal: collapsible sections |
| Mobile-2 | HIGH | 1d | Mini-header shows current screen name |
| Mobile-3 | MEDIUM | 1d | Touch-friendly button minimum size |

---

## Phase 3B: Interactive Chat (CRITICAL)

**Goal:** Real-time model interaction with streaming

### Chat Screen Features

| Feature | Priority | Effort | Description |
|---------|----------|--------|-------------|
| Chat-1 | HIGH | 3d | Basic chat screen with input/output |
| Chat-2 | HIGH | 2d | Streaming response display |
| Chat-3 | HIGH | 1d | Tool call rendering |
| Chat-4 | MEDIUM | 1d | Model selector dropdown |
| Chat-5 | MEDIUM | 1d | Message history scroll |

---

## Phase 3C: Comprehensive Benchmarking

**Goal:** Full feature parity with benchmark-lmstudio.py

### Enhanced Metrics

| Feature | Priority | Effort | Description |
|---------|----------|--------|-------------|
| Bench-1 | HIGH | 2d | Load time tracking (JIT detection) |
| Bench-2 | HIGH | 1d | Statistical aggregation (min/max/avg/stddev) |
| Bench-3 | HIGH | 1d | Winner detection per category |
| Bench-4 | MEDIUM | 1d | Prompt set library integration |
| Bench-5 | MEDIUM | 1d | Multiple output format export |

---

## Phase 4: Advanced Features

| Feature | Priority | Effort | Description |
|---------|----------|--------|-------------|
| Multi-1 | LOW | 5d | Server switching UI |
| Multi-2 | LOW | 3d | Multi-server monitoring |
| SSE-1 | MEDIUM | 3d | SSE stream wiring |
| Test-1 | HIGH | 5d | Test suite implementation |

---

## Benchmark Requirements (from benchmark-lmstudio.py)

### Core Metrics

| Metric | Source | Description |
|--------|--------|-------------|
| TPS | Calculated | Completion tokens / elapsed time |
| TTFT | Wall-clock | Time to first token |
| TPOT | Calculated | Time per output token |
| Reasoning Tokens | `reasoning_content` | Chain-of-thought token count |
| Tool Accuracy | Schema validation | Correct tool calls / total |
| Load Time | Polling | JIT model loading time |

### Benchmark Modes

| Mode | Description | Phases |
|------|-------------|--------|
| quick | Throughput only | warm (TPS, TTFT) |
| tool | Throughput + tool | warm + tool (tool accuracy) |
| full | Load + throughput + tool | load + warm + tool |

### Output Formats

| Format | Use Case |
|--------|----------|
| text | Human-readable with bar charts |
| json | Machine parsing with statistics |
| csv | Spreadsheet import |
| csv-full | Detailed per-run analysis |

---

## Quick Reference

### Current Working Features
- ✅ Dashboard with model cards
- ✅ Model Manager with 12-row table
- ✅ Live Monitor with TPS/TTFT metrics
- ✅ Benchmark runner (basic)
- ✅ Settings with server config
- ✅ Portrait/landscape responsive

### Known Limitations
- No navigation focus indicators
- No interactive chat
- No load time tracking in benchmark
- No statistical aggregation