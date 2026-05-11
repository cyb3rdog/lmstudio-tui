from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static


class ShortcutsModal(ModalScreen[None]):
    """Keyboard shortcuts reference overlay."""

    DEFAULT_CSS = """
    ShortcutsModal > Vertical {
        background: $surface;
        border: thick $primary;
        width: 90%;
        max-width: 58;
        height: auto;
        max-height: 90%;
        padding: 1 2;
        align: center middle;
    }
    ShortcutsModal Label { margin-bottom: 1; }
    ShortcutsModal .shortcuts-body { margin-bottom: 1; }
    ShortcutsModal Horizontal { height: auto; align: center middle; margin-top: 1; }
    ShortcutsModal Button { margin: 0 1; }
    """

    BINDINGS = [
        ("escape", "dismiss_modal", "Close"),
        ("?", "dismiss_modal", "Close"),
    ]

    _HELP = """\
[bold]Navigation[/bold]
  [cyan]1-6[/cyan]             Switch screens
  [cyan]Ctrl+B[/cyan]          Toggle sidebar
  [cyan]Escape[/cyan]          Focus nav / collapse sidebar
  [cyan]Tab / Shift+Tab[/cyan]  Next / previous widget

[bold]Model Manager[/bold]
  [cyan]L[/cyan]  Load selected model
  [cyan]U[/cyan]  Unload selected model
  [cyan]D[/cyan]  Download selected model
  [cyan]R[/cyan]  Refresh list

[bold]Chat[/bold]
  [cyan]Enter[/cyan]   Send message
  [cyan]Ctrl+L[/cyan]  Clear conversation
  [cyan]Stop[/cyan]    Abort streaming response

[bold]Benchmark[/bold]
  [cyan]Start[/cyan]         Begin benchmark run
  [cyan]Stop[/cyan]          Abort running benchmark
  [cyan]Select All[/cyan]    Mark all models
  [cyan]Deselect All[/cyan]  Clear model selection
  [cyan]Full (all)[/cyan]    Enable all benchmark modes
  [cyan]Export[/cyan]        Save results (JSON / CSV / Markdown)

[bold]Live Monitor[/bold]
  [cyan]P[/cyan]  Pause / Resume

[bold]Global[/bold]
  [cyan]Ctrl+Q[/cyan]  Quit
  [cyan]Ctrl+R[/cyan]  Reconnect servers
  [cyan]?[/cyan]       This help"""

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("[bold]Keyboard Shortcuts[/bold]")
            yield Static(self._HELP, classes="shortcuts-body")
            with Horizontal():
                yield Button("Close  [Esc]", variant="primary", id="btn-close")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()

    def action_dismiss_modal(self) -> None:
        self.dismiss()
