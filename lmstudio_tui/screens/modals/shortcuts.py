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
  [cyan]1[/cyan] Dashboard  [cyan]2[/cyan] Models  [cyan]3[/cyan] Chat  [cyan]4[/cyan] Monitor
  [cyan]5[/cyan] Benchmark  [cyan]6[/cyan] Hub     [cyan]7[/cyan] Settings
  [cyan]Ctrl+B[/cyan]  Toggle sidebar
  [cyan]Escape[/cyan]  Focus nav / second press collapses
  [cyan]Tab / Shift+Tab[/cyan]  Next / prev widget

[bold]Model Manager[/bold]
  [cyan]L[/cyan]  Load selected      [cyan]U[/cyan]  Unload selected
  [cyan]D[/cyan]  Open Hub screen    [cyan]R[/cyan]  Refresh list

[bold]Hub[/bold]
  [cyan]Enter[/cyan]  Search / confirm model ID
  [cyan]↓ Download[/cyan]  Send selected model to LM Studio

[bold]Chat[/bold]
  [cyan]Enter[/cyan]    Send message
  [cyan]Ctrl+L[/cyan]   Clear conversation
  [cyan]■ Stop[/cyan]   Abort streaming response

[bold]Benchmark[/bold]
  [cyan]▶ Start / ■ Stop[/cyan]  Run / abort
  [cyan]✓ All / ✗ None[/cyan]   Select / deselect all models
  [cyan]Full (all)[/cyan]         Enable all modes
  [cyan]⬇ Export[/cyan]          Save JSON / CSV / Markdown

[bold]Monitor[/bold]
  [cyan]P[/cyan]  Pause / Resume

[bold]Global[/bold]
  [cyan]Ctrl+Q[/cyan]  Quit    [cyan]Ctrl+R[/cyan]  Reconnect    [cyan]?[/cyan]  This help"""

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
