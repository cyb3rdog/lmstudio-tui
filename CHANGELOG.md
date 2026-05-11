# Changelog

## [Unreleased]

### Architecture Refactor
- **ModelManager** (screen 2) is now purely load/unload/refresh — no download logic
- **Download Manager** (screen 6) is self-contained — browse HF, start downloads, track progress, cancel
- Removed download poll/cancel infrastructure from `model_manager.py` (all moved to `download_manager.py`)
- Deleted `screens/hub.py` shim — `DownloadManager` imported directly from `screens/download_manager.py`
- Consistent naming throughout: screen label "Downloads", class `DownloadManager`, file `download_manager.py`

---

## [0.1.0] - Initial Release

### Features
- Dashboard with server status and model cards
- Model Manager with load/unload/download
- Model Hub browser (HuggingFace GGUF search)
- Streaming Chat interface
- Benchmark Runner (throughput, tool calling, parallel modes)
- Live Monitor with TPS/TTFT sparklines
- Settings with server configuration
- Responsive layout (portrait/landscape)
- Keyboard shortcuts overlay (`?`)

### Test Coverage
- 212 tests passing
