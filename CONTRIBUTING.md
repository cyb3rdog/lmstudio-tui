# Contributing to LM Studio TUI

Thank you for your interest in contributing!

## Development Setup

```bash
# Fork → clone → venv
git clone https://github.com/YOUR_USERNAME/lmstudio-tui.git
cd lmstudio-tui
python -m venv .venv
source .venv/bin/activate

# Install with dev dependencies
pip install -e ".[dev]"
```

## Running the App

```bash
lmstudio-tui                              # connect to localhost:1234
lmstudio-tui --endpoint http://host:1234  # remote server
```

## Running Tests

```bash
pytest              # all tests (expect ~212 passing)
pytest -v           # verbose output
pytest tests/test_*.py::test_name  # run specific test
```

## Code Style

| Rule | Tool | Config |
|------|------|--------|
| Import sorting | `isort` | `pyproject.toml` `[tool.isort]` |
| Formatting | `ruff format` | defaults |
| Linting | `ruff check` | defaults |

Run before every commit:

```bash
ruff check . && ruff format .
```

### Specific Conventions

- **Type hints** — required on all public functions/methods; prefer `list[T]` over `List[T]`.
- **Docstrings** — class-level docstring required; method docstrings for anything non-trivial.
- **`from __future__ import annotations`** — always present at top of `.py` files.
- **No bare `except:`** — always catch specific exceptions or use `except Exception`.
- **`async`/`await`** — use `textual` workers (`@work`) for background tasks; never `asyncio.run()` in screen methods.
- **No blocking I/O** — all HTTP, file, and subprocess calls must be async.
- **No hardcoded magic numbers** — put shared values in `constants.py`.
- **Dead code** — if a widget/module is unused but planned, add a docstring note; don't just leave orphan classes.

## Architecture

### Screen Navigation

All screen switches go through `app.action_goto(screen_id)`:
- `action_goto("dashboard")`, `action_goto("models")`, etc.
- Numbers `1`–`7` trigger the same via bindings in `app.py`.

Avoid calling `push_screen()` directly for screen navigation — use `_switch_to()` via the action to keep nav-tabs and ContentSwitcher in sync.

### State

- `ServerRegistry` — connection state, per-server `LMStudioClient` instances.
- `MetricsStore` — ring buffer of performance samples per server+model.

Both are constructed in `app.py.__init__` and passed down via `screen.app.{registry,metrics_store}`.

### API Layer

`api/client.py` wraps all LM Studio v1 REST calls. Screens get a client via:

```python
client = self.app.server_registry.get_client(server_name)
```

## Pull Request Process

1. **Branch**: `git checkout -b feature/your-feature`
2. **Develop**: make changes, run `ruff check . && ruff format . && pytest`
3. **Test**: new features require tests in `tests/`
4. **Commit**: conventional commits — `feat:`, `fix:`, `docs:`, `refactor:`, `test:`
5. **Push & PR**: open against `main`, describe the change and any migration concerns

### PR Checklist

- [ ] All `pytest` tests pass
- [ ] `ruff check .` — no errors or warnings
- [ ] New code has type hints
- [ ] New public APIs documented (docstrings)
- [ ] New `constants.py` values added if applicable
- [ ] CHANGELOG.md updated (add under `[Unreleased]`)
- [ ] README.md updated if user-facing behaviour changed

## Project Structure

```
lmstudio_tui/
├── api/           # LM Studio v1 API client, HuggingFace Hub client
│   ├── client.py  # Core httpx wrapper
│   ├── models.py  # Pydantic request/response models
│   ├── hub.py     # HuggingFace GGUF search
│   └── sse.py     # Planned: SSE log streaming (unused)
├── benchmark/     # Benchmark engine, analysis, export
├── config/       # TOML models and file loader
├── screens/      # Textual screens (Dashboard, Models, Chat, ...)
│   └── modals/   # Onboarding, ServerForm, ModelLoad, Shortcuts, Confirm
├── state/        # ServerRegistry, MetricsStore
├── utils/        # Formatting helpers
├── widgets/      # ModelCard, MetricPanel, ComparisonChart (planned)
├── app.py        # App root, bindings, navigation
├── app.tcss      # Global CSS
└── constants.py  # Shared thresholds, timeouts, window sizes
```

## Reporting Issues

When opening an issue, include:

```
- Python version
- lmstudio-tui version (`python -c "import lmstudio_tui; print(lmstudio_tui.__version__)"`)
- OS and terminal (e.g. macOS, iTerm2, 120×40)
- Steps to reproduce
- Expected vs actual behaviour
- `lmstudio-tui --help` output
```

## Release Process (for maintainers)

1. Update `pyproject.toml` version
2. Update `CHANGELOG.md` — move `[Unreleased]` items to a new `[0.x.0]` section with date
3. Tag: `git tag -a v0.x.0 -m "Release v0.x.0" && git push --tags`
4. Publish to PyPI: `pip build . && twine upload dist/*`