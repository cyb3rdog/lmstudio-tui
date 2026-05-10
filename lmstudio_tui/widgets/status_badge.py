from __future__ import annotations

from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label

from ..state.server_registry import ConnectionState


_ICONS = {
    ConnectionState.CONNECTED: ("●", "status-connected"),
    ConnectionState.CONNECTING: ("◌", "status-connecting"),
    ConnectionState.DISCONNECTED: ("○", "status-disconnected"),
    ConnectionState.ERROR: ("✗", "status-error"),
}


class StatusBadge(Widget):
    """Small colored indicator showing a server connection state."""

    DEFAULT_CSS = """
    StatusBadge {
        width: auto;
        height: 1;
    }
    StatusBadge Label { width: auto; }
    .status-connected    { color: $success; }
    .status-connecting   { color: $warning; }
    .status-disconnected { color: $text-muted; }
    .status-error        { color: $error; }
    """

    state: reactive[ConnectionState] = reactive(ConnectionState.DISCONNECTED)

    def compose(self):
        icon, css_class = _ICONS[self.state]
        yield Label(icon, classes=css_class, id="badge-icon")

    def watch_state(self, state: ConnectionState) -> None:
        icon, css_class = _ICONS[state]
        try:
            lbl = self.query_one("#badge-icon", Label)
            lbl.update(icon)
            lbl.set_classes(css_class)
        except Exception:
            pass
