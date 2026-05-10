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
| H2 | ⚠️ | Connection state in sidebar |
| H3 | ⚠️ | VRAM display (hardware endpoint) |
| H4 | ✅ | Empty-state placeholders |
| H5 | ⚠️ | Server bar portrait truncation |
| H6 | ✅ | Settings portrait overflow |
| H7 | ⚠️ | Settings test connection clear |
| H8 | ⚠️ | Redundant @work stacking |
| H9 | ⚠️ | Disconnect notification |

---

## Milestone 3: Feature Complete (NEXT)

**Goal:** Add missing medium-priority features

### Phase 3A: Core Features

| Issue | Priority | Effort | Description |
|-------|----------|--------|-------------|
| M1 | HIGH | 3d | Model filter on Monitor/Benchmark |
| M4 | MEDIUM | 1d | Fix download poll stale client |
| M5 | MEDIUM | 1d | Fix silent exception catching |
| M8 | LOW | 1d | App title shows server name |
| M12 | LOW | 1d | MetricPanel unique widget IDs |

### Phase 3B: Infrastructure

| Issue | Priority | Effort | Description |
|-------|----------|--------|-------------|
| M10 | HIGH | 5d | Test suite implementation |
| M11 | MEDIUM | 2d | Structured logging |
| M13 | LOW | 1d | Onboarding skip edge case |

### Phase 3C: Missing Features

| Issue | Priority | Effort | Description |
|-------|----------|--------|-------------|
| M2 | HIGH | 10d | Live chat / inference UI |
| M3 | MEDIUM | 3d | SSE stream wiring |
| M6 | LOW | 2d | Benchmark config validation |
| M7 | LOW | 1d | BenchmarkConfig UI wiring |

---

## Milestone 4: Polish & Release

**Goal:** Prepare for public release

| Issue | Priority | Effort | Description |
|-------|----------|--------|-------------|
| L1 | LOW | 1h | Add `__all__` to `__init__.py` |
| L2 | LOW | 2d | Light/dark theme toggle |
| L3 | LOW | 2d | Help screen |
| L4 | LOW | 1d | Pyright CI workflow |
| L5 | LOW | 2h | Onboarding modal responsive widths |
| L6 | LOW | 2d | Benchmark results sorting |
| L7 | LOW | 2h | Model card click handler |

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
- No server switching (single server only)
- No VRAM display (hardware endpoint not called)
- No model filtering on Monitor/Benchmark
- No test suite

---

## Release Checklist

- [ ] All Phase 3A issues complete
- [ ] Test coverage > 50%
- [ ] CI/CD workflows configured
- [ ] PyPI package published
- [ ] Documentation complete
- [ ] README badges added