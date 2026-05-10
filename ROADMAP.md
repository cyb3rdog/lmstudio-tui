# LM Studio TUI - Roadmap

## Current Status: ✅ Phase 1 & 2 Complete

All critical and high-priority issues have been resolved. The TUI is production-ready for single-server use cases.

**Last Updated:** 2026-05-10

---

## Milestone 1: Core Stability ✅ COMPLETE

**Goal:** Fix all critical bugs preventing basic functionality

| Issue | Status | Notes |
|-------|--------|-------|
| C1 | ✅ | Silent auth failure detection |
| C2 | ✅ | Benchmark Start button off-screen |
| C3 | ✅ | Select model toast dismisses |
| C4 | ✅ | Onboarding sets active_server |
| C5 | ✅ | Config TOML crash handling |
| C6 | ✅ | remove_server orphans _active |
| C7 | ✅ | ComparisonChart renders |
| C8 | ✅ | Sidebar nav in portrait |
| RC1 | ✅ | Race condition fix |
| RC2 | ✅ | Retry on connection not ready |

---

## Milestone 2: Production Ready ✅ COMPLETE

**Goal:** Resolve all high-priority UX issues

| Issue | Status | Notes |
|-------|--------|-------|
| H1 | ⚠️ | Server switcher UI |
| H2 | ✅ | Connection state in sidebar |
| H3 | ⚠️ | VRAM display (hardware endpoint) |
| H4 | ✅ | Empty-state placeholders |
| H5 | ✅ | Server bar portrait truncation |
| H6 | ✅ | Settings portrait overflow |
| H7 | ⚠️ | Settings test connection clear |
| H8 | ⚠️ | Redundant @work stacking |
| H9 | ⚠️ | Disconnect notification |

---

## Milestone 3: Navigation & Mobile Optimization (NEXT)

**Goal:** Optimize navigation, mobile portrait UX, and comprehensive benchmarking

### Phase 3A: Navigation Improvements (HIGH PRIORITY)

| Feature | Priority | Effort | Description |
|---------|----------|--------|-------------|
| Nav-1 | HIGH | 2d | Keyboard navigation enhancements (vim-style hjkl, tab order) |
| Nav-2 | HIGH | 1d | Focus indicators for all interactive elements |
| Nav-3 | HIGH | 1d | Quick search/filter within screens |
| Nav-4 | MEDIUM | 2d | Breadcrumb navigation for nested actions |
| Nav-5 | MEDIUM | 1d | Keyboard shortcuts help overlay |

### Phase 3B: Mobile Portrait Optimization (HIGH PRIORITY)

| Feature | Priority | Effort | Description |
|---------|----------|--------|-------------|
| Mobile-1 | HIGH | 2d | Responsive layouts for 50×24 terminal |
| Mobile-2 | HIGH | 2d | Collapsible sections on small screens |
| Mobile-3 | HIGH | 1d | Touch-friendly button sizing |
| Mobile-4 | MEDIUM | 1d | Auto-hide server bar in portrait |
| Mobile-5 | MEDIUM | 1d | Modal dialogs responsive redesign |

### Phase 3C: Comprehensive Benchmarking (HIGH PRIORITY)

| Feature | Priority | Effort | Description |
|---------|----------|--------|-------------|
| Bench-1 | HIGH | 3d | Multi-model comparison matrix |
| Bench-2 | HIGH | 2d | Statistical significance testing (std dev, confidence intervals) |
| Bench-3 | HIGH | 2d | Export to CSV/JSON with full metrics |
| Bench-4 | MEDIUM | 2d | Prompt set library (creative, code, chat, reasoning) |
| Bench-5 | MEDIUM | 2d | Concurrent benchmark runs |
| Bench-6 | MEDIUM | 1d | Custom prompt input |
| Bench-7 | LOW | 2d | Benchmark result history/trends |

---

## Milestone 4: Advanced Features (FUTURE)

**Goal:** Add sophisticated features and multi-server support

### Phase 4A: Multi-Server Support (DEFERRED)

| Feature | Priority | Effort | Description |
|---------|----------|--------|-------------|
| Multi-1 | LOW | 5d | Server switching UI |
| Multi-2 | LOW | 3d | Multi-server monitoring |
| Multi-3 | LOW | 2d | Cross-server model sync |

### Phase 4B: Feature Completion

| Feature | Priority | Effort | Description |
|---------|----------|--------|-------------|
| M2 | HIGH | 10d | Live chat / inference UI |
| M3 | MEDIUM | 3d | SSE stream wiring |
| M10 | HIGH | 5d | Test suite implementation |
| M11 | MEDIUM | 2d | Structured logging |

---

## Benchmark Requirements (Inspired by benchmark-lmstudio.py)

### Benchmark Modes

| Mode | Description | Includes |
|------|-------------|----------|
| **quick** | Throughput only (default) | TPS, TTFT, basic metrics |
| **tool** | Throughput + tool calling | All quick metrics + tool accuracy |
| **full** | Load time + throughput + tool calling | All metrics + model load time |

### Core Metrics to Track

| Metric | Source | Description |
|--------|--------|-------------|
| **TPS (Tokens Per Second)** | Server `stats` | Token generation speed |
| **TTFT (Time To First Token)** | Wall-clock | Latency for first response |
| **TPOT (Time Per Output Token)** | Calculated | Average time per token |
| **VRAM Usage** | Hardware endpoint | GPU memory consumption |
| **Context Length** | Config | Model context window |
| **Batch Size** | Config | Concurrent requests |
| **Reasoning Tokens** | `reasoning_content` | Chain-of-thought token count |
| **Tool Accuracy** | Tool schema validation | Correct tool calls / total |

### Prompt Sets for Comprehensive Testing

| Set | Purpose | Sample Size | Example Prompts |
|-----|---------|-------------|-----------------|
| **creative** | Story generation, creative writing | 10 prompts | "Write a sci-fi story about AI..." |
| **code** | Code completion, debugging | 10 prompts | "Fix this Python bug: ..." |
| **chat** | Conversational AI, Q&A | 10 prompts | "Explain quantum computing..." |
| **reasoning** | Logic puzzles, math problems | 10 prompts | "If X=5 and Y=X*3..." |
| **mixed** | Balanced across all categories | 20 prompts | Rotating selection |

### Benchmark Output Formats

| Format | Use Case | Structure |
|--------|----------|-----------|
| **text** | Human inspection (TTY) | Bar charts, winner verdict |
| **json** | Machine parsing | Full session with statistics |
| **csv** | Spreadsheet import | One row per model summary |
| **csv-full** | Detailed analysis | One row per run |

### JSON Output Structure

```json
{
  "session_id": "20260510173000",
  "timestamp": "2026-05-10T17:30:00",
  "server": "https://lmstudio.phact.cz",
  "mode": "quick",
  "config": {
    "runs_per_phase": 3,
    "timeout_s": 120,
    "temperature": 0.2,
    "max_tokens": 512
  },
  "summary": {
    "total_models": 12,
    "successful_models": 10,
    "failed_models": 2,
    "total_tokens": 12500,
    "duration_s": 180
  },
  "winners": {
    "throughput": {"model_id": "model-x", "tps": 45.2},
    "tool": {"model_id": "model-y", "accuracy_pct": 100.0}
  },
  "results": [
    {
      "model_id": "model-x",
      "model_state": "loaded",
      "load_time_ms": 15000,
      "warm": {
        "tps_avg": 45.2,
        "tps_min": 42.1,
        "tps_max": 48.3,
        "ttft_avg_ms": 1250,
        "successes": 3,
        "total_tokens": 3840,
        "reasoning_tokens": 150
      },
      "tool": {
        "tps_avg": 0,
        "tool_calls_made": 0
      },
      "runs": [
        {
          "phase": "warm",
          "success": true,
          "elapsed_ms": 2100,
          "tokens": 128,
          "tps": 45.2,
          "ttft_ms": 1250,
          "prompt_tokens": 15,
          "reasoning_tokens": 5,
          "has_tool": false
        }
      ]
    }
  ]
}
```

### Advanced Features from benchmark-lmstudio.py

| Feature | Description |
|---------|-------------|
| **Winner Detection** | Identifies best model per category (throughput, tool accuracy) |
| **Load Time Tracking** | Measures JIT model loading time separately |
| **Statistical Aggregation** | Min/max/avg/stddev for TPS and TTFT |
| **Reasoning Token Detection** | Extracts `reasoning_content` token count |
| **Tool Call Validation** | Validates tool arguments against expected result |
| **Session Export** | Saves full results to JSON file |

---

## Quick Reference

### Current Working Features
- ✅ Dashboard with model cards
- ✅ Model Manager with 12-row table
- ✅ Live Monitor with TPS/TTFT metrics
- ✅ Benchmark runner with export
- ✅ Settings with server config
- ✅ Portrait/landscape responsive

### Known Limitations
- No VRAM display (hardware endpoint not called)
- No model filtering on Monitor/Benchmark
- No test suite

---

## Release Checklist

- [ ] All Phase 3A navigation improvements complete
- [ ] All Phase 3B mobile optimizations complete
- [ ] All Phase 3C benchmark features complete
- [ ] Test coverage > 50%
- [ ] CI/CD workflows configured
- [ ] PyPI package published
- [ ] Documentation complete
- [ ] README badges added