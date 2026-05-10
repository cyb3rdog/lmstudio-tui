from __future__ import annotations

from dataclasses import dataclass

from rich import box
from rich.table import Table
from rich.text import Text
from textual.reactive import reactive
from textual.widget import Widget


@dataclass
class ChartRow:
    label: str
    value: float | None
    unit: str = ""
    pending: bool = False


class ComparisonChart(Widget):
    """Horizontal ASCII bar chart comparing benchmark results across models."""

    DEFAULT_CSS = """
    ComparisonChart {
        height: auto;
        padding: 0 1;
    }
    """

    rows: reactive[list[ChartRow]] = reactive(list)

    BAR_WIDTH = 36

    def render(self):
        if not self.rows:
            return Text("No results yet", style="dim")

        table = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
        table.add_column("label", style="bold", width=24, no_wrap=True)
        table.add_column("bar", width=self.BAR_WIDTH + 2)
        table.add_column("value", width=14, justify="right")

        max_val = max((r.value for r in self.rows if r.value is not None), default=1.0) or 1.0

        for row in self.rows:
            if row.pending or row.value is None:
                bar = Text("░" * self.BAR_WIDTH, style="dim")
                val_text = Text("pending", style="dim")
            else:
                filled = max(1, int((row.value / max_val) * self.BAR_WIDTH))
                bar = Text("█" * filled + "░" * (self.BAR_WIDTH - filled), style="green")
                val_text = Text(f"{row.value:.1f} {row.unit}", style="bright_green")
            table.add_row(Text(row.label[:24], style="bold"), bar, val_text)

        return table
