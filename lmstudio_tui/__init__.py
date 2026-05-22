"""LM Studio TUI — Terminal UI for managing, monitoring, chatting with, and benchmarking LM Studio servers."""

from importlib.metadata import version as _get_version

try:
    __version__ = _get_version("lmstudio-tui")
except Exception:
    __version__ = "0.2.0"