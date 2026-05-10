from __future__ import annotations

from dataclasses import dataclass

from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Label, ProgressBar, Select, Static
from textual import work

from ..api.models import CompletionMetrics
from ..utils.formatting import format_ms, format_tps
from ..widgets.comparison_chart import ChartRow, ComparisonChart


class BenchmarkRunner(Widget):
    DEFAULT_CSS = """
    BenchmarkRunner {
        width: 1fr;
        height: 1fr;
    }
    BenchmarkRunner #config-panel {
        height: auto;
        padding: 1;
        background: $surface-darken-1;
        border-bottom: solid $primary-darken-3;
    }
    BenchmarkRunner #config-row { height: auto; }
    BenchmarkRunner #config-row Label { margin: 0 1; width: auto; }
    BenchmarkRunner #config-row Input { width: 8; }
    BenchmarkRunner #config-row Select { width: 18; }
    BenchmarkRunner #progress-bar-row {
        height: 3;
        padding: 0 1;
        background: $surface-darken-1;
        border-bottom: solid $primary-darken-3;
    }
    BenchmarkRunner #progress-bar-row.-hidden { display: none; }
    BenchmarkRunner #results-table { height: 1fr; }
    BenchmarkRunner #comparison-section {
        height: auto;
        border-top: solid $primary-darken-3;
        padding: 0 1;
    }
    BenchmarkRunner #comparison-title {
        color: $primary;
        text-style: bold;
        padding: 0 1;
        height: 1;
    }
    BenchmarkRunner #btn-row { height: auto; padding: 0 1; }
    BenchmarkRunner #btn-row Button { margin: 0 1 0 0; }
    """

    running: reactive[bool] = reactive(False)

    def compose(self) -> ComposeResult:
        with Vertical(id="config-panel"):
            with Horizontal(id="config-row"):
                yield Label("Prompt set:")
                yield Select(
                    [("short", "short"), ("medium", "medium"), ("long", "long"),
                     ("code", "code"), ("mixed", "mixed")],
                    value="mixed",
                    id="sel-prompts",
                )
                yield Label("Samples:")
                yield Input(value="10", id="inp-samples")
                yield Label("Temp:")
                yield Input(value="0.0", id="inp-temp")
                yield Label("Max tokens:")
                yield Input(value="256", id="inp-maxtok")
            with Horizontal(id="btn-row"):
                yield Button("▶ Start", id="btn-start", variant="primary")
                yield Button("■ Stop", id="btn-stop", variant="error")
                yield Button("⬇ Export", id="btn-export", variant="default")
        with Horizontal(id="progress-bar-row", classes="-hidden"):
            yield Label("", id="prog-label")
            yield ProgressBar(id="prog-bar", total=100, show_eta=False)
        yield DataTable(id="results-table", cursor_type="row")
        with Vertical(id="comparison-section"):
            yield Label("  COMPARISON", id="comparison-title")
            yield ComparisonChart(id="chart")

    def on_mount(self) -> None:
        table = self.query_one("#results-table", DataTable)
        table.add_columns("#", "Model", "TTFT", "TPS", "In / Out", "Total ms")
        self._results: list = []
        self._run_count = 0
        self._stop_requested = False

    def _config(self) -> dict:
        return {
            "prompt_set": str(self.query_one("#sel-prompts", Select).value),
            "samples": max(1, int(self.query_one("#inp-samples", Input).value or "10")),
            "temperature": float(self.query_one("#inp-temp", Input).value or "0.0"),
            "max_tokens": int(self.query_one("#inp-maxtok", Input).value or "256"),
        }

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-start" and not self.running:
            self._start_benchmark()
        elif event.button.id == "btn-stop":
            self._stop_requested = True
            self.running = False
        elif event.button.id == "btn-export":
            self._export_results()

    def watch_running(self, running: bool) -> None:
        prog_row = self.query_one("#progress-bar-row")
        if running:
            prog_row.remove_class("-hidden")
        else:
            prog_row.add_class("-hidden")

    def _start_benchmark(self) -> None:
        client = self.app.server_registry.active_client
        if not client:
            self.notify("No server connected", severity="error")
            return

        self._stop_requested = False
        self._run_count = 0
        self._results = []
        self.query_one("#results-table", DataTable).clear()
        self.query_one(ComparisonChart).rows = []
        self.running = True
        self._run_benchmark(self._config())

    @work
    async def _run_benchmark(self, cfg: dict) -> None:
        from ..benchmark.engine import BenchmarkEngine, BenchmarkSpec
        client = self.app.server_registry.active_client
        if not client:
            return

        try:
            models = await client.list_models()
            loaded = [m for m in models if m.is_loaded]
        except Exception as e:
            self.notify(str(e), severity="error")
            self.running = False
            return

        if not loaded:
            self.notify("No models are currently loaded", severity="warning")
            self.running = False
            return

        engine = BenchmarkEngine(client, self.app.metrics_store, self.app.server_registry.active_name)

        chart_rows: dict[str, ChartRow] = {}
        for model in loaded:
            chart_rows[model.id] = ChartRow(label=model.id, value=None, unit="t/s", pending=True)

        for model in loaded:
            if self._stop_requested:
                break

            spec = BenchmarkSpec(
                model_id=model.id,
                prompt_set=cfg["prompt_set"],
                runs=cfg["samples"],
                temperature=cfg["temperature"],
                max_tokens=cfg["max_tokens"],
                warmup=self.app.config.benchmark.warmup_runs,
            )

            self.query_one("#prog-label", Label).update(f"  Running: {model.id}  ")
            async for event in engine.run(spec):
                if self._stop_requested:
                    break
                if event.get("type") == "sample":
                    self._run_count += 1
                    m: CompletionMetrics = event["metrics"]
                    table = self.query_one("#results-table", DataTable)
                    table.add_row(
                        str(self._run_count),
                        model.id[:28],
                        format_ms(m.time_to_first_token_ms),
                        format_tps(m.tokens_per_second),
                        f"{m.prompt_tokens}/{m.completion_tokens}",
                        f"{m.total_duration_ms:.0f}" if m.total_duration_ms else "—",
                    )
                    pct = int((event["run"] / spec.runs) * 100)
                    self.query_one("#prog-bar", ProgressBar).update(progress=pct)

                elif event.get("type") == "done":
                    result = event["result"]
                    chart_rows[model.id] = ChartRow(
                        label=model.id,
                        value=result.mean_tps,
                        unit="t/s",
                        pending=False,
                    )
                    self.query_one(ComparisonChart).rows = list(chart_rows.values())
                    self._results.append(result)

        self.running = False
        self.notify("Benchmark complete", severity="information")

    def _export_results(self) -> None:
        if not self._results:
            self.notify("No results to export", severity="warning")
            return
        self._do_export(self._results)

    @work
    async def _do_export(self, results: list) -> None:
        from ..benchmark.export import ReportExporter
        import pathlib, time
        export_dir = pathlib.Path(self.app.config.benchmark.export_dir).expanduser()
        ts = time.strftime("%Y%m%d-%H%M%S")
        exporter = ReportExporter(export_dir)
        paths = exporter.export_all(results, f"benchmark-{ts}")
        self.notify(f"Exported to {export_dir}", severity="information")
