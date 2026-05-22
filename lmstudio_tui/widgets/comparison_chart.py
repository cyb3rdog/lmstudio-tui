from __future__ import annotations

from dataclasses import dataclass

from rich import box
from rich.table import Table
from rich.text import Text
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static


@dataclass
class ChartRow:
    label: str
    value: float | None
    unit: str = ""
    pending: bool = False


class ComparisonChart(Widget):
    """Widget for rendering benchmark comparison charts (planned feature).

This widget is defined but not yet integrated into any screen.
Planned for: benchmark runner comparison view (Phase 9 / Bench-adv).

To use: import and add to a screen's compose(), wire up `rows` reactive attribute.
"""

    rows: reactive[list[ChartRow]] = reactive(list)

    BAR_WIDTH = 36

    def compose(self) -> ComposeResult:
        yield Static("", id="chart-content")

    def watch_rows(self, rows: list[ChartRow]) -> None:
        try:
            content = self.query_one("#chart-content", Static)
        except Exception:
            # Not yet mounted — defer until compose sets up children
            return
        if not rows:
            content.update("[dim]No results yet[/dim]")
        else:
            content.update(self._build_table(rows))

    def _build_table(self, rows: list[ChartRow]) -> Table:
        if not rows:
            return Table()

        table = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
        table.add_column("label", style="bold", width=24, no_wrap=True)
        table.add_column("bar", width=self.BAR_WIDTH + 2)
        table.add_column("value", width=14, justify="right")

        max_val = max((r.value for r in rows if r.value is not None), default=1.0) or 1.0

        for row in rows:
            if row.pending or row.value is None:
                bar = Text("░" * self.BAR_WIDTH, style="dim")
                val_text = Text("pending", style="dim")
            else:
                filled = max(1, int((row.value / max_val) * self.BAR_WIDTH))
                bar = Text("█" * filled + "░" * (self.BAR_WIDTH - filled), style="green")
                val_text = Text(f"{row.value:.1f} {row.unit}", style="bright_green")
            table.add_row(Text(row.label[:24], style="bold"), bar, val_text)

        return table
