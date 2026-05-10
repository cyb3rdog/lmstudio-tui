from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Label, ProgressBar, Select, Static
from textual import work

from ..api.models import CompletionMetrics
from ..benchmark.engine import BenchmarkMode
from ..utils.formatting import format_ms, format_tps
from ..widgets.comparison_chart import ChartRow, ComparisonChart


def _fmt(v: float | None, decimals: int = 1) -> str:
    return f"{v:.{decimals}f}" if v is not None else "—"


def _pct(v: float | None) -> str:
    return f"{v * 100:.1f}%" if v is not None else "—"


class BenchmarkRunner(Widget):
    DEFAULT_CSS = """
    BenchmarkRunner {
        width: 1fr;
        height: 1fr;
    }
    BenchmarkRunner #config-panel {
        height: auto;
        padding: 0 1;
        background: $surface-darken-1;
        border-bottom: solid $primary-darken-3;
    }
    BenchmarkRunner .config-row {
        height: auto;
        padding: 0;
        align: left middle;
    }
    BenchmarkRunner .config-row.stacked { layout: vertical; }
    BenchmarkRunner .config-row Label { margin: 0 1; width: auto; }
    BenchmarkRunner .config-row Input { width: 8; }
    BenchmarkRunner .config-row Select { width: 20; }
    BenchmarkRunner #mode-row { height: 3; }
    BenchmarkRunner #params-row { height: 3; }
    BenchmarkRunner #btn-row { height: 3; }
    BenchmarkRunner #btn-row Button { margin: 0 1 0 0; }
    BenchmarkRunner #progress-bar-row {
        height: 3;
        padding: 0 1;
        background: $surface-darken-1;
        border-bottom: solid $primary-darken-3;
        align: left middle;
    }
    BenchmarkRunner #progress-bar-row.-hidden { display: none; }
    BenchmarkRunner #prog-bar { width: 1fr; }
    BenchmarkRunner #results-table { height: 1fr; }
    BenchmarkRunner #comparison-section {
        height: auto;
        max-height: 10;
        border-top: solid $primary-darken-3;
        padding: 0 1;
    }
    BenchmarkRunner #comparison-title {
        color: $primary;
        text-style: bold;
        padding: 0 1;
        height: 1;
    }
    """

    running: reactive[bool] = reactive(False)

    def compose(self) -> ComposeResult:
        with Vertical(id="config-panel"):
            with Horizontal(classes="config-row", id="mode-row"):
                yield Label("Mode:")
                yield Select(
                    [
                        (BenchmarkMode.THROUGHPUT, "throughput"),
                        (BenchmarkMode.TOOL_CALLING, "tool_calling"),
                        (BenchmarkMode.LOAD_TIME, "load_time"),
                        (BenchmarkMode.PARALLEL, "parallel"),
                    ],
                    value=BenchmarkMode.THROUGHPUT,
                    id="sel-mode",
                )
                yield Label("Prompt set:")
                yield Select(
                    [("short", "short"), ("medium", "medium"), ("long", "long"),
                     ("code", "code"), ("mixed", "mixed")],
                    value="mixed",
                    id="sel-prompts",
                )
                yield Label("Tool subset:")
                yield Select(
                    [("all", "all"), ("calculator", "calculator"), ("weather", "weather"),
                     ("string", "string"), ("search", "search")],
                    value="all",
                    id="sel-tools",
                )
            with Horizontal(classes="config-row", id="params-row"):
                yield Label("Samples:")
                yield Input(value="10", id="inp-samples")
                yield Label("Temp:")
                yield Input(value="0.0", id="inp-temp")
                yield Label("Max tokens:")
                yield Input(value="256", id="inp-maxtok")
                yield Label("Parallel slots:")
                yield Input(value="4", id="inp-slots")
            with Horizontal(classes="config-row", id="btn-row"):
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
        table.add_columns("#", "Model", "Mode", "TTFT", "TPS", "TPOT", "In/Out", "Tool✓", "Args", "Load ms")
        self._results: list = []
        self._run_count = 0
        self._stop_requested = False
        self._update_layout()

    def on_resize(self) -> None:
        self._update_layout()

    def _update_layout(self) -> None:
        stacked = self.size.width < 80
        for row_id in ("mode-row", "params-row", "btn-row"):
            try:
                row = self.query_one(f"#{row_id}")
                if stacked:
                    row.add_class("stacked")
                else:
                    row.remove_class("stacked")
            except Exception:
                pass

    def _config(self) -> dict:
        def _int(widget_id: str, default: int) -> int:
            try:
                return max(1, int(self.query_one(f"#{widget_id}", Input).value or str(default)))
            except ValueError:
                return default

        def _float(widget_id: str, default: float) -> float:
            try:
                return float(self.query_one(f"#{widget_id}", Input).value or str(default))
            except ValueError:
                return default

        return {
            "mode": str(self.query_one("#sel-mode", Select).value),
            "prompt_set": str(self.query_one("#sel-prompts", Select).value),
            "tool_subset": str(self.query_one("#sel-tools", Select).value),
            "samples": _int("inp-samples", 10),
            "temperature": _float("inp-temp", 0.0),
            "max_tokens": _int("inp-maxtok", 256),
            "parallel_slots": _int("inp-slots", 4),
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
        from ..benchmark.analysis import detect_winners
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

        mode = cfg["mode"]

        # Load time mode doesn't need a loaded model — just any available model
        if mode == BenchmarkMode.LOAD_TIME:
            available = models
        else:
            available = loaded

        if not available:
            self.notify("No models available", severity="warning")
            self.running = False
            return

        engine = BenchmarkEngine(client, self.app.metrics_store, self.app.server_registry.active_name)
        chart_rows: dict[str, ChartRow] = {}
        for model in available:
            chart_rows[model.id] = ChartRow(label=model.id, value=None, unit="t/s", pending=True)

        for model in available:
            if self._stop_requested:
                break

            spec = BenchmarkSpec(
                model_id=model.id,
                mode=mode,
                prompt_set=cfg["prompt_set"],
                runs=cfg["samples"],
                warmup=getattr(self.app.config.benchmark, "warmup_runs", 2),
                temperature=cfg["temperature"],
                max_tokens=cfg["max_tokens"],
                tool_subset=cfg["tool_subset"],
                parallel_slots=cfg["parallel_slots"],
                parallel_total=cfg["samples"],
            )

            self.query_one("#prog-label", Label).update(f"  {model.id}  ")
            total_runs = cfg["samples"]

            async for event in engine.run(spec):
                if self._stop_requested:
                    break

                if event.get("type") == "sample":
                    self._run_count += 1
                    m: CompletionMetrics = event["metrics"]
                    table = self.query_one("#results-table", DataTable)
                    table.add_row(
                        str(self._run_count),
                        model.id[:20],
                        mode[:6],
                        format_ms(m.time_to_first_token_ms),
                        format_tps(m.tokens_per_second),
                        _fmt(m.tpot_ms, 0) + "ms" if m.tpot_ms is not None else "—",
                        f"{m.prompt_tokens}/{m.completion_tokens}",
                        "✓" if m.tool_name_correct else ("✗" if m.tool_name_correct is False else "—"),
                        _fmt(m.tool_args_score, 2) if m.tool_args_score is not None else "—",
                        _fmt(m.load_time_ms, 0) + "ms" if m.load_time_ms is not None else "—",
                    )
                    run_num = event.get("run", self._run_count)
                    pct = int((run_num / max(total_runs, 1)) * 100)
                    self.query_one("#prog-bar", ProgressBar).update(progress=pct)

                elif event.get("type") == "done":
                    result = event["result"]
                    chart_value = result.mean_tps or result.parallel_tps
                    chart_rows[model.id] = ChartRow(
                        label=model.id, value=chart_value, unit="t/s", pending=False
                    )
                    self.query_one(ComparisonChart).rows = list(chart_rows.values())
                    self._results.append(result)

        # Winner detection across all models
        detect_winners(self._results)

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
