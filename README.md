# LM Studio TUI

A terminal-based UI for managing, monitoring, chatting with, and benchmarking [LM Studio](https://lmstudio.ai) servers — from any terminal, including mobile (SSH/Termux).

## Features

| Screen | What it does |
|--------|--------------|
| **Dashboard** | Server status bar, loaded model cards with TPS/TTFT sparklines, unloaded model summary |
| **Models** | Full model table (status, quantization, context size); Load/Unload/Download with keyboard shortcuts |
| **Chat** | Streaming chat with any loaded model; history, Stop, Clear (`Ctrl+L`) |
| **Monitor** | Live 1-second TPS & TTFT sparklines per model; recent-requests table; Pause (`P`) |
| **Benchmark** | Multi-model, multi-mode benchmarking (throughput, tool calling, parallel); CSV/JSON/Markdown export |
| **Settings** | Server CRUD, connection test, poll interval preference |

### Download Manager (screen `6`)

Press **6** or **D** from the Models screen to open the **Downloads** screen — a full-screen, searchable browser of GGUF models from HuggingFace. Default view shows the top 60 models by download count. Search by name, select a row, click **↓ Download** and the download starts on your LM Studio server while you watch progress.

## Installation

### Local development

```bash
git clone https://github.com/cyb3rdog/lmstudio-tui.git
cd lmstudio-tui
pip install -e .
```

### PyPI

```bash
pip install lmstudio-tui
```

## Quick start

```bash
# Connect to LM Studio running on localhost
lmstudio-tui

# Connect to a remote server
lmstudio-tui --endpoint http://192.168.1.100:1234 --api-key your-key
```

On first launch with no config file, an onboarding dialog asks for the server endpoint and API key (the key can be left blank if auth is disabled).

## Command-line options

```
usage: lmstudio-tui [-h] [--endpoint ENDPOINT] [--api-key API_KEY]

  --endpoint ENDPOINT   Server URL (e.g. http://192.168.1.100:1234)
  --api-key API_KEY     API key (leave empty if auth is disabled)
```

## Configuration

`~/.lmstudio-tui/config.toml` is created automatically on first run:

```toml
active_server = "local"

[[servers]]
name = "local"
endpoint = "http://localhost:1234"
api_key = ""

[benchmark]
export_dir = "~/.lmstudio-tui/benchmarks"

[ui]
poll_interval_s = 3.0
```

## Keyboard shortcuts

### Global

| Key | Action |
|-----|--------|
| `1` – `7` | Dashboard / Models / Chat / Monitor / Benchmark / Downloads / Settings |
| `Ctrl+B` | Toggle sidebar |
| `Escape` | Focus nav sidebar (second press collapses it) |
| `?` | Show keyboard-shortcuts overlay |
| `Ctrl+R` | Force reconnect to all servers |
| `Ctrl+Q` | Quit |

### Models screen

| Key | Action |
|-----|--------|
| `L` | Load selected model |
| `U` | Unload selected model |
| `D` | Open Download Manager (browse & download) |
| `R` | Refresh model list |

### Monitor screen

| Key | Action |
|-----|--------|
| `P` | Pause / Resume live refresh |

### Chat screen

| Key | Action |
|-----|--------|
| `Ctrl+L` | Clear chat history |
| `Enter` | Send message |

### Benchmark screen

| Key | Action |
|-----|--------|
| `S` | Start benchmark |
| `X` | Stop benchmark |

## Requirements

- Python 3.11+
- LM Studio 0.3+ (v1 API)
- Terminal with Unicode and color support
- Internet access on the TUI host for Download Manager search (download is performed by the LM Studio server)

## Development

```bash
pip install -e ".[dev]"
pytest              # 212 tests
```

### Project structure

```
lmstudio_tui/
├── api/            # LMStudioClient (httpx), HuggingFace Hub client
├── benchmark/      # Engine, analysis, export
├── config/         # TOML models and loader
├── screens/        # Dashboard, Models, Chat, Monitor, Benchmark, DownloadManager, Settings
│   └── modals/     # ConfirmModal, ModelLoadModal, OnboardingModal, ServerForm, ShortcutsModal
├── state/          # ServerRegistry, MetricsStore
├── utils/          # Formatting helpers
└── widgets/        # ModelCard, MetricPanel, ComparisonChart, …
```

## Known limitations

- **TTFT** is wall-clock time from request to first chunk; LM Studio's `stats` field is always empty.
- **VRAM** shows `—`; the LM Studio v1 API does not expose per-model VRAM usage.
- **Download cancel** is best-effort; the server may continue downloading. There is no cancel API in LM Studio v1.
- **reasoning_tokens** is a streaming chunk-count proxy, not real token counts.
- **prompt_tokens** for streaming chat responses is `0`; LM Studio does not send `usage` in streaming chunks.

## License

MIT — see [LICENSE](LICENSE).
