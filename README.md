# LM Studio TUI

A terminal-based user interface for remote management, monitoring, and benchmarking of LM Studio servers.

![LM Studio TUI Demo](https://via.placeholder.com/800x400?text=LM+Studio+TUI+Screenshot)

## Features

- **Dashboard** - View loaded models and server status
- **Model Manager** - Load, unload, and download models
- **Live Monitor** - Real-time TPS and TTFT metrics
- **Benchmark Runner** - Performance testing across loaded models
- **Settings** - Server configuration and preferences

## Installation

### From PyPI (when published)

```bash
pip install lmstudio-tui
```

### From Source

```bash
git clone https://github.com/cyb3rdog/lmstudio-tui.git
cd lmstudio-tui
pip install -e .
```

## Usage

### Quick Start

Run with default configuration:

```bash
lmstudio-tui
```

### With Server Configuration

```bash
lmstudio-tui --endpoint https://lmstudio.phact.cz --api-key your-key
```

### Command Line Options

```
usage: lmstudio-tui [-h] [--endpoint ENDPOINT] [--api-key API_KEY]

options:
  -h, --help            show this help message and exit
  --endpoint ENDPOINT   LM Studio server endpoint
  --api-key API_KEY     API key for authentication
```

## Configuration

Configuration is stored at `~/.lmstudio-tui/config.toml`:

```toml
active_server = "LMStudio"

[[servers]]
name = "LMStudio"
endpoint = "https://lmstudio.phact.cz"
api_key = "your-api-key"

[benchmark]
default_prompt_set = "mixed"
default_samples = 10
warmup_runs = 2
export_dir = "~/.lmstudio-tui/benchmarks"

[ui]
poll_interval_s = 3.0
theme = "textual-dark"
```

## Navigation

| Key | Action |
|-----|--------|
| `1-5` | Switch between screens (Dashboard, Models, Monitor, Benchmark, Settings) |
| `Ctrl+B` | Toggle sidebar |
| `Escape` | Return focus to navigation |
| `P` | Pause/Resume live monitor |
| `R` | Refresh current screen |
| `Ctrl+Q` | Quit |

### Screen Shortcuts

- **Dashboard**: `L` (Load), `U` (Unload), `D` (Download)
- **Model Manager**: `L` (Load), `U` (Unload), `D` (Download), `R` (Refresh)

## Requirements

- Python 3.11+
- LM Studio server (v1 API)
- Terminal with Unicode support

## Development

### Setup

```bash
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest
```

### Project Structure

```
lmstudio-tui/
├── lmstudio_tui/
│   ├── __init__.py
│   ├── __main__.py
│   ├── app.py              # Main application
│   ├── app.tcss            # Styles
│   ├── api/                # API client
│   ├── benchmark/          # Benchmark engine & export
│   ├── config/             # Configuration models & loader
│   ├── screens/            # UI screens
│   ├── state/              # Server registry, metrics store
│   ├── utils/              # Formatting helpers
│   └── widgets/            # Custom widgets
├── pyproject.toml
└── README.md
```

## Troubleshooting

### "No server connected" error

1. Verify the server endpoint is accessible
2. Check your API key is correct
3. Ensure the LM Studio server is running

### Empty model list

1. Check server connection in Dashboard
2. Verify models are loaded on the server
3. Check firewall/proxy settings

### Terminal too small

The TUI requires minimum 60 columns width. Use landscape mode or resize your terminal.

## License

MIT License - see LICENSE file for details.

## Acknowledgments

Built with [Textual](https://textual.textualize.io/) for the terminal UI framework.