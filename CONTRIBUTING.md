# Contributing to LM Studio TUI

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing.

## Development Setup

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/lmstudio-tui.git
   cd lmstudio-tui
   ```
3. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
4. Install in development mode:
   ```bash
   pip install -e ".[dev]"
   ```

## Running the Application

```bash
lmstudio-tui
```

Or with a specific server:

```bash
lmstudio-tui --endpoint https://your-server.com --api-key your-key
```

## Running Tests

```bash
pytest
```

## Code Style

- Follow PEP 8 guidelines
- Use type hints for all public functions
- Write docstrings for classes and methods
- Keep functions focused and small

## Pull Request Process

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make your changes
3. Run tests: `pytest`
4. Commit with clear message: `git commit -m "feat: add new feature"`
5. Push to your fork: `git push origin feature/your-feature`
6. Open a pull request

## Project Structure

```
lmstudio_tui/
├── api/           # LM Studio API client
├── benchmark/     # Benchmark engine and export
├── config/        # Configuration management
├── screens/       # Textual screens (Dashboard, Models, etc.)
├── state/         # Server registry, metrics store
├── utils/         # Helper functions
└── widgets/       # Custom Textual widgets
```

## Reporting Issues

Use the GitHub issue tracker. Please include:
- Python version
- Operating system
- Terminal type and size
- Steps to reproduce
- Expected vs actual behavior