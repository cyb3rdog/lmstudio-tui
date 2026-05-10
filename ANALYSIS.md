# LM Studio TUI - System Analysis & Revised Roadmap

## 1. Benchmark Requirements - Systematic Analysis

### 1.1 From benchmark-lmstudio.py (Production CLI)

**Core Purpose:** Measure model performance for throughput, latency, and tool-calling capability

**Benchmark Modes:**
| Mode | Description | What It Measures |
|------|-------------|------------------|
| `quick` | Default, throughput only | TPS, TTFT, basic timing |
| `tool` | Throughput + tool calling | All quick + tool accuracy |
| `full` | Load + throughput + tool | All metrics + load time |

**Core Metrics (from RunData dataclass):**
- `elapsed_ms` - Total run time
- `tokens` - Completion tokens
- `tps` - Tokens per second (calculated)
- `ttft_ms` - Time to first token
- `prompt_tokens` - Input tokens
- `reasoning_tokens` - Chain-of-thought tokens (if supported)
- `has_tool` - Tool call detected
- `tool_correct` - Tool arguments match expected
- `error` - Failure reason

**Phase Aggregation (PhaseAggregate):**
- Success/failure counts
- TPS: avg, min, max
- TTFT: avg, min, max (ms)
- Total tokens, prompt tokens, reasoning tokens
- Tool calls: made, correct

**Output Formats:**
- `text` - Human-readable with bar charts, winner verdict
- `json` - Full session data with statistics
- `csv` - One row per model summary
- `csv-full` - One row per run (detailed)

**Key Features Missing in TUI:**
- [ ] Load time tracking (JIT model loading)
- [ ] Tool calling benchmark phase
- [ ] Statistical aggregation (min/max/avg/stddev)
- [ ] Winner detection (best model per category)
- [ ] Reasoning token tracking
- [ ] Multiple output formats
- [ ] Prompt set library

---

## 2. Navigation Analysis

### 2.1 Current Implementation

**Sidebar Navigation:**
- ListView with 5 items (Dashboard, Models, Monitor, Benchmark, Settings)
- Number keys 1-5 switch screens directly
- Ctrl+B toggles sidebar visibility
- Escape returns focus to nav

**Portrait Mode:**
- Sidebar auto-hides below 70 columns
- Mini-header shows: `LM Studio ○ server-name [1] [2] [3] [4] [5]`
- Nav highlights immediately switch screens (no enter needed)

### 2.2 Issues Identified

**Problems:**
1. **No visual focus indication** when sidebar is hidden
2. **Arrow navigation** only works in sidebar, not in content
3. **Escape always goes to nav** even if already focused
4. **No breadcrumb** for nested actions
5. **Ctrl+B is non-standard** - should be Tab or dedicated key

**Requirements for Native TUI Feel:**
- Tab cycles between sidebar and content
- Enter activates highlighted item
- Arrow keys navigate within screens
- Escape always returns to nav (consistent)
- Visual focus ring on all interactive elements
- Collapsible sections with arrow keys

---

## 3. UX Design Review

### 3.1 Current State

**Working:**
- Dashboard shows model cards
- Model manager has 12-row table
- Live monitor shows TPS/TTFT
- Benchmark runs basic tests
- Settings saves config

**Issues:**
- No focus indicators on buttons/inputs
- Modal dialogs not responsive
- No keyboard shortcuts help
- Empty states could be more helpful
- No search/filter in any screen

### 3.2 Mobile Portrait (50×24) Issues

- Sidebar completely hidden
- Config panel buttons wrap but overflow
- Server bar truncates
- No way to see current screen context

---

## 4. Chat/Interactive Mode - Critical Missing Feature

### 4.1 Why It's Important

Looking at the original benchmark-lmstudio.py:
- It's a **core use case** - interactive inference
- Users need to **test models in real-time**
- **Tool calling** requires interactive testing
- **Reasoning tokens** only visible in streaming responses

### 4.2 Required Features

| Feature | Priority | Description |
|---------|----------|-------------|
| Chat input | HIGH | Text input with Enter to send |
| Streaming display | HIGH | Live token-by-token output |
| Tool call rendering | HIGH | Show tool calls and results |
| Reasoning display | HIGH | Show chain-of-thought separately |
| Message history | MEDIUM | Scrollable conversation |
| Model selector | HIGH | Quick switch between loaded models |

---

## 5. Revised Roadmap

### Phase 3A: Core UX Foundation (HIGH PRIORITY)

| Feature | Effort | Description |
|---------|--------|-------------|
| Nav-1 | 1d | Tab cycle between sidebar and content |
| Nav-2 | 1d | Visual focus indicators on all widgets |
| Nav-3 | 1d | Keyboard shortcuts overlay (F1 or ?) |
| Nav-4 | 1d | Better Escape handling (consistent nav return) |
| Mobile-1 | 2d | 50×24 terminal: collapsible sections |
| Mobile-2 | 1d | Mini-header shows current screen name |

### Phase 3B: Interactive Chat (HIGH PRIORITY)

| Feature | Effort | Description |
|---------|--------|-------------|
| Chat-1 | 3d | Basic chat screen with input/output |
| Chat-2 | 2d | Streaming response display |
| Chat-3 | 1d | Tool call rendering |
| Chat-4 | 1d | Model selector dropdown |
| Chat-5 | 1d | Message history scroll |

### Phase 3C: Comprehensive Benchmarking (HIGH PRIORITY)

| Feature | Effort | Description |
|---------|--------|-------------|
| Bench-1 | 2d | Load time tracking (JIT detection) |
| Bench-2 | 1d | Statistical aggregation (min/max/avg) |
| Bench-3 | 1d | Winner detection per category |
| Bench-4 | 1d | Prompt set library integration |
| Bench-5 | 1d | Multiple output format export |

### Phase 4: Advanced Features

| Feature | Priority | Effort |
|---------|----------|--------|
| Multi-server | LOW | 5d |
| SSE streaming | MEDIUM | 3d |
| Test suite | HIGH | 5d |

---

## 6. Immediate Next Steps

1. **Fix navigation UX:**
   - Add Tab binding to cycle focus
   - Add focus styles to all widgets
   - Make Escape consistently return to nav

2. **Add Chat screen:**
   - New screen with message display
   - Input at bottom
   - Streaming support

3. **Enhance benchmark:**
   - Add load time tracking
   - Add statistical summary
   - Add winner detection

---

## 7. Key Decisions Needed

1. **Navigation model:** Keep sidebar + number keys OR switch to tab-based?
2. **Chat placement:** New screen (6th) or integrated into existing?
3. **Benchmark scope:** Full parity with CLI or minimum viable?
4. **Mobile first:** Should 50×24 be primary target instead of 80×24?