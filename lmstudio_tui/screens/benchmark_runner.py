from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import (
    Button, Checkbox, DataTable, Input, Label, ProgressBar,
    SelectionList, Static,
)
from textual.widgets.selection_list import Selection
from textual import work

from ..api.models import CompletionMetrics, LoadRequest
from ..benchmark.engine import BenchmarkEngine, BenchmarkMode, BenchmarkSpec
from ..benchmark.analysis import BenchmarkResult, analyze, detect_winners
from ..utils.formatting import format_ms, format_tps


def _fmt(v: float | None, decimals: int = 1, suffix: str = "") -> str:
    if v is None:
        return "—"
    return f"{v:.{decimals}f}{suffix}"


def _pct(v: float | None) -> str:
    return f"{v * 100:.0f}%" if v is not None else "—"


@dataclass
class _ModelEntry:
    id: str
    is_loaded: bool
    instance_id: str | None = None


class BenchmarkRunner(Widget):
    """Agentic benchmark runner.

    Flow:
      1. Load model list from server (loaded + not loaded).
      2. User checks models and modes to run.
      3. On Start: unload all → for each checked model:
         load → capture load_ms → run checked modes → unload.
      4. Per-sample rows appear in real time; summary updates per model.
    """

    DEFAULT_CSS = """
    BenchmarkRunner {
        width: 1fr;
        height: 1fr;
        layout: vertical;
    }

    /* ── Config panel ────────────────────────────────────────────── */
    BenchmarkRunner #config-panel {
        height: auto;
        background: $surface-darken-1;
        border-bottom: solid $primary-darken-3;
        padding: 0 1;
    }
    BenchmarkRunner #model-list {
        height: 6;
        max-height: 10;
        border: solid $primary-darken-3;
    }
    BenchmarkRunner #model-actions {
        height: auto;
    }
    BenchmarkRunner #model-actions Button {
        width: auto;
        margin: 0 1 0 0;
    }
    BenchmarkRunner #mode-row {
        height: auto;
    }
    BenchmarkRunner #mode-row Checkbox {
        margin: 0 1 0 0;
        width: auto;
    }
    BenchmarkRunner #params-row {
        height: auto;
    }
    BenchmarkRunner #params-row Label {
        width: auto;
        margin: 0 1 0 0;
    }
    BenchmarkRunner #params-row Input {
        width: 6;
    }
    BenchmarkRunner #btn-row {
        height: auto;
    }
    BenchmarkRunner #btn-row Button {
        margin: 0 1 0 0;
        width: auto;
    }

    /* ── Narrow: params stack into multiple rows ─────────────────────── */
    BenchmarkRunner #params-row.stacked {
        layout: vertical;
        height: auto;
    }
    BenchmarkRunner #params-row.stacked .param-pair {
        height: 3;
    }
    BenchmarkRunner #params-row.stacked .param-pair Label {
        width: 12;
        height: 3;
        content-align: right middle;
    }
    BenchmarkRunner #params-row.stacked .param-pair Input {
        width: 1fr;
    }

    /* ── Narrow: model-actions buttons stack ────────────────────────── */
    BenchmarkRunner #model-actions.stacked Button {
        width: 1fr;
        margin: 0 0 0 0;
    }

    /* ── Progress ────────────────────────────────────────────────── */
    BenchmarkRunner #progress-panel {
        height: 3;
        padding: 0 1;
        background: $surface-darken-1;
        border-bottom: solid $primary-darken-3;
        align: left middle;
    }
    BenchmarkRunner #progress-panel.-hidden { display: none; }
    BenchmarkRunner #prog-bar { width: 1fr; }
    BenchmarkRunner #prog-label { width: auto; margin-right: 1; }

    /* ── Summary ─────────────────────────────────────────────────── */
    BenchmarkRunner #summary-panel {
        height: auto;
        max-height: 8;
        border-bottom: solid $primary-darken-3;
        padding: 0 1;
        background: $surface-darken-1;
    }
    BenchmarkRunner #summary-title {
        color: $primary;
        text-style: bold;
        height: 1;
    }
    BenchmarkRunner #summary-content {
        height: auto;
        color: $text-muted;
    }

    /* ── Results ─────────────────────────────────────────────────── */
    BenchmarkRunner #results-table { height: 1fr; }
    """

    running: reactive[bool] = reactive(False)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._model_entries: list[_ModelEntry] = []
        self._results: list[BenchmarkResult] = []
        self._run_count = 0
        self._stop = asyncio.Event()
        # Defer results table column setup until first resize when width is known.
        self._table_columns_setup = False

    # ── compose ───────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        with ScrollableContainer(id="config-panel"):
            yield SelectionList[str](id="model-list")
            with Horizontal(id="model-actions"):
                yield Button("✓ All",      id="btn-sel-all",        variant="default")
                yield Button("✗ None",     id="btn-desel-all",      variant="default")
                yield Button("↺ Refresh",  id="btn-refresh-models", variant="default")
                yield Button("▶ Start",    id="btn-start",          variant="primary")
                yield Button("■ Stop",     id="btn-stop",           variant="error")
                yield Button("⬇ Export",   id="btn-export",         variant="default")
            with Horizontal(id="mode-row"):
                yield Checkbox("Throughput",  id="chk-throughput", value=True)
                yield Checkbox("Tool Calling", id="chk-tool",      value=False)
                yield Checkbox("Parallel",    id="chk-parallel",   value=False)
                yield Button("Full (all)", id="btn-full-mode", variant="default")
            with Horizontal(id="params-row"):
                with Horizontal(classes="param-pair"):
                    yield Label("Samples:")
                    yield Input("10", id="inp-samples")
                with Horizontal(classes="param-pair"):
                    yield Label("Warmup:")
                    yield Input("2", id="inp-warmup")
                with Horizontal(classes="param-pair"):
                    yield Label("Temp:")
                    yield Input("0.0", id="inp-temp")
                with Horizontal(classes="param-pair"):
                    yield Label("Max tok:")
                    yield Input("256", id="inp-maxtok")
                with Horizontal(classes="param-pair"):
                    yield Label("Slots:")
                    yield Input("4", id="inp-slots")
                with Horizontal(classes="param-pair"):
                    yield Label("Ctx len:")
                    yield Input("", id="inp-ctx", placeholder="auto")

        # Summary — always visible above results
        with Vertical(id="summary-panel"):
            yield Label("  SUMMARY", id="summary-title")
            yield Static("No results yet.", id="summary-content")

        # Progress bar
        with Horizontal(id="progress-panel", classes="-hidden"):
            yield Label("", id="prog-label")
            yield ProgressBar(id="prog-bar", total=100, show_eta=False)

        # Per-sample results table
        yield DataTable(id="results-table", cursor_type="row")

    def on_mount(self) -> None:
        # Do NOT set up table columns here — self.size.width is 0 at mount time.
        self._update_layout()
        self._load_model_list()

    def on_show(self) -> None:
        if not self.running:
            self._load_model_list()

    def on_resize(self) -> None:
        self._update_layout()
        # Set up results table columns on first resize when width is known.
        if not self._table_columns_setup:
            self._table_columns_setup = True
            self._setup_results_table()

    def _update_layout(self) -> None:
        w = self.size.width
        try:
            params = self.query_one("#params-row")
            actions = self.query_one("#model-actions")
            if w < 70:
                params.add_class("stacked")
                actions.add_class("stacked")
            else:
                params.remove_class("stacked")
                actions.remove_class("stacked")
        except Exception:
            pass

    def _setup_results_table(self) -> None:
        table = self.query_one("#results-table", DataTable)
        # Guard: if columns already exist, clear rows only (not columns).
        # Duplicate column setup causes misalignment in _add_row.
        if table.columns:
            table.clear()
            return
        w = self.size.width
        if w < 60:
            table.add_columns("#", "Model", "Mode", "TPS", "TTFT", "Load ms")
        else:
            table.add_columns(
                "#", "Model", "Mode", "TPS", "TTFT", "TPOT",
                "Prompt/Out", "Tool✓", "Load ms"
            )

    # ── model list ────────────────────────────────────────────────────────────

    @work(exclusive=True)
    async def _load_model_list(self) -> None:
        client = self.app.server_registry.active_client
        if not client:
            for _ in range(20):
                await asyncio.sleep(0.25)
                client = self.app.server_registry.active_client
                if client:
                    break
        if not client:
            return

        try:
            models = await client.list_models()
        except Exception as e:
            self.notify(str(e), severity="error")
            return

        self._model_entries = [
            _ModelEntry(id=m.id, is_loaded=m.is_loaded, instance_id=m.instance_id)
            for m in models
        ]

        sl = self.query_one("#model-list", SelectionList)
        sl.clear_options()
        for m in models:
            status = "●" if m.is_loaded else "○"
            label = f"{status} {m.id}"
            sl.add_option(Selection(label, m.id, initial_state=True))

    # ── events ────────────────────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "btn-start":
                if not self.running:
                    self._start_benchmark()
            case "btn-stop":
                self._stop.set()
                self.running = False
            case "btn-export":
                self._export_results()
            case "btn-sel-all":
                self.query_one("#model-list", SelectionList).select_all()
            case "btn-desel-all":
                self.query_one("#model-list", SelectionList).deselect_all()
            case "btn-refresh-models":
                self._load_model_list()
            case "btn-full-mode":
                for chk_id in ("chk-throughput", "chk-tool", "chk-parallel"):
                    self.query_one(f"#{chk_id}", Checkbox).value = True
        event.stop()

    def watch_running(self, running: bool) -> None:
        prog = self.query_one("#progress-panel")
        if running:
            prog.remove_class("-hidden")
        else:
            prog.add_class("-hidden")

    # ── benchmark orchestration ───────────────────────────────────────────────

    def _config(self) -> dict:
        def _int(wid: str, default: int) -> int:
            try:
                return max(1, int(self.query_one(f"#{wid}", Input).value or str(default)))
            except ValueError:
                return default

        def _flt(wid: str, default: float) -> float:
            try:
                return float(self.query_one(f"#{wid}", Input).value or str(default))
            except ValueError:
                return default

        def _int_opt(wid: str) -> int | None:
            """Parse an optional integer field; returns None if blank."""
            try:
                val = self.query_one(f"#{wid}", Input).value.strip()
                return int(val) if val else None
            except ValueError:
                return None

        selected_models = list(self.query_one("#model-list", SelectionList).selected)
        modes = []
        if self.query_one("#chk-throughput", Checkbox).value:
            modes.append(BenchmarkMode.THROUGHPUT)
        if self.query_one("#chk-tool", Checkbox).value:
            modes.append(BenchmarkMode.TOOL_CALLING)
        if self.query_one("#chk-parallel", Checkbox).value:
            modes.append(BenchmarkMode.PARALLEL)

        return {
            "selected_models": selected_models,
            "modes": modes,
            "samples": _int("inp-samples", 10),
            "warmup": _int("inp-warmup", 2),
            "temperature": _flt("inp-temp", 0.0),
            "max_tokens": _int("inp-maxtok", 256),
            "parallel_slots": _int("inp-slots", 4),
            "context_length": _int_opt("inp-ctx"),
        }

    def _start_benchmark(self) -> None:
        cfg = self._config()
        if not cfg["selected_models"]:
            self.notify("Select at least one model", severity="warning")
            return
        if not cfg["modes"]:
            self.notify("Select at least one mode", severity="warning")
            return
        client = self.app.server_registry.active_client
        if not client:
            self.notify("No server connected", severity="error")
            return

        self._stop.clear()
        self._run_count = 0
        self._results = []  # clear previous run results to prevent accumulation
        self.query_one("#results-table", DataTable).clear()
        self.query_one("#summary-content", Static).update("Running…")
        self._run_benchmark(cfg)
        self.running = True

    @work(exclusive=True)
    async def _run_benchmark(self, cfg: dict) -> None:
        client = self.app.server_registry.active_client
        if not client:
            self.running = False
            return

        selected_ids: list[str] = cfg["selected_models"]
        modes: list[str] = cfg["modes"]

        # ── Step 1: Unload all currently loaded models ────────────────────
        self._set_progress("Unloading all models…", 0)
        try:
            models = await client.list_models()
            for m in models:
                if m.is_loaded and m.instance_id:
                    await client.unload_model(m.instance_id)
                    await asyncio.sleep(0.3)
        except Exception as e:
            self.notify(f"Unload failed: {e}", severity="error")
            self.running = False
            return

        model_results: dict[str, list[BenchmarkResult]] = {}
        engine = BenchmarkEngine(
            client, self.app.metrics_store,
            self.app.server_registry.active_name
        )

        total_work = len(selected_ids) * len(modes)
        work_done = 0

        # ── Step 2: For each selected model ──────────────────────────────
        for model_id in selected_ids:
            if self._stop.is_set():
                break

            model_results[model_id] = []

            # ── Load model + capture load time ────────────────────────────
            self._set_progress(f"Loading  {model_id[:30]}…", 0)
            try:
                body: dict = {"model": model_id}
                ctx = cfg.get("context_length")
                if ctx:
                    body["context_length"] = ctx
                t_wall = time.perf_counter()
                from ..api.models import LoadResponse
                raw = await client._post("/api/v1/models/load", body)
                wall_ms = (time.perf_counter() - t_wall) * 1000.0
                load_resp = LoadResponse.model_validate(raw)
                instance_id = load_resp.instance_id
                # Prefer server's own timing; fall back to wall-clock
                load_ms = (
                    load_resp.load_time_seconds * 1000.0
                    if load_resp.load_time_seconds > 0
                    else wall_ms
                )
            except Exception as e:
                self.notify(f"Load failed ({model_id}): {e}", severity="error")
                continue

            # Record a load-time row in the results table
            self._add_row(
                model_id, "load",
                tps=None, ttft_ms=None, tpot_ms=None,
                prompt_tokens=0, completion_tokens=0,
                tool_correct=None, load_ms=load_ms,
            )

            # ── Run each selected mode ────────────────────────────────────
            for mode in modes:
                if self._stop.is_set():
                    break

                samples: list[CompletionMetrics] = []
                warmup = cfg["warmup"] if mode == BenchmarkMode.THROUGHPUT else 1

                spec = BenchmarkSpec(
                    model_id=model_id,
                    mode=mode,
                    prompt_set="mixed",
                    runs=cfg["samples"],
                    warmup=warmup,
                    temperature=cfg["temperature"],
                    max_tokens=cfg["max_tokens"],
                    tool_subset="all",
                    parallel_slots=cfg["parallel_slots"],
                    parallel_total=cfg["samples"],
                )

                run_num = 0
                async for event in engine.run(spec):
                    if self._stop.is_set():
                        break
                    if event["type"] == "sample":
                        run_num = event["run"]
                        m: CompletionMetrics = event["metrics"]
                        samples.append(m)
                        self._add_row(
                            model_id, mode[:6],
                            tps=m.tokens_per_second,
                            ttft_ms=m.time_to_first_token_ms,
                            tpot_ms=m.tpot_ms,
                            prompt_tokens=m.prompt_tokens,
                            completion_tokens=m.completion_tokens,
                            tool_correct=m.tool_name_correct,
                            load_ms=None,
                        )
                        pct = int((run_num / max(cfg["samples"], 1)) * 100)
                        self._set_progress(
                            f"{model_id[:20]} | {mode[:10]} | {run_num}/{cfg['samples']}",
                            pct
                        )
                    elif event["type"] == "error":
                        self.notify(f"Run {event['run']} error: {event['error']}", severity="warning")

                if samples:
                    result = analyze(samples, model_id, self.app.server_registry.active_name, mode=mode)
                    model_results[model_id].append(result)
                    self._results.append(result)

                work_done += 1

            # ── Unload model ──────────────────────────────────────────────
            try:
                models_now = await client.list_models()
                info = next((m for m in models_now if m.id == model_id), None)
                if info and info.instance_id:
                    await client.unload_model(info.instance_id)
                    await asyncio.sleep(0.2)
            except Exception:
                pass

        # ── Step 3: Detect winners and show summary ───────────────────────
        if self._results:
            detect_winners(self._results)
            self._update_summary()

        self.running = False
        self._set_progress("", 0)
        if not self._stop.is_set():
            self.notify("Benchmark complete", severity="information")

    # ── helpers ───────────────────────────────────────────────────────────────

    def _set_progress(self, label: str, pct: int) -> None:
        try:
            self.query_one("#prog-label", Label).update(f"  {label}  ")
            self.query_one("#prog-bar", ProgressBar).update(progress=pct)
        except Exception:
            pass

    def _add_row(
        self,
        model_id: str,
        mode: str,
        *,
        tps: float | None,
        ttft_ms: float | None,
        tpot_ms: float | None,
        prompt_tokens: int,
        completion_tokens: int,
        tool_correct: bool | None,
        load_ms: float | None,
    ) -> None:
        self._run_count += 1
        table = self.query_one("#results-table", DataTable)
        col_count = len(table.columns)
        if col_count == 6:
            # Narrow table: #, Model, Mode, TPS, TTFT, Load ms
            table.add_row(
                str(self._run_count),
                model_id[:14],
                mode[:4],
                format_tps(tps),
                format_ms(ttft_ms),
                _fmt(load_ms, 0, "ms") if load_ms is not None else "—",
            )
        elif col_count == 9:
            # Wide table: #, Model, Mode, TPS, TTFT, TPOT, Prompt/Out, Tool✓, Load ms
            tool_str = (
                "✓" if tool_correct is True
                else "✗" if tool_correct is False
                else "—"
            )
            table.add_row(
                str(self._run_count),
                model_id[:22],
                mode,
                format_tps(tps),
                format_ms(ttft_ms),
                _fmt(tpot_ms, 0, "ms") if tpot_ms is not None else "—",
                f"{prompt_tokens}/{completion_tokens}" if prompt_tokens or completion_tokens else "—",
                tool_str,
                _fmt(load_ms, 0, "ms") if load_ms is not None else "—",
            )
        else:
            # Unexpected column count — log and fall back to 6-column format.
            table.add_row(
                str(self._run_count),
                model_id[:22],
                mode[:4],
                format_tps(tps),
                format_ms(ttft_ms),
                _fmt(load_ms, 0, "ms") if load_ms is not None else "—",
            )

    def _update_summary(self) -> None:
        lines: list[str] = []
        # Group results by model_id
        by_model: dict[str, list[BenchmarkResult]] = {}
        for r in self._results:
            by_model.setdefault(r.model_id, []).append(r)

        for model_id, results in by_model.items():
            parts = [f"[bold]{model_id[:28]}[/bold]"]
            for r in results:
                mode_tag = r.mode[:5]
                if r.mode == BenchmarkMode.THROUGHPUT:
                    w = " [bold yellow]★[/bold yellow]" if r.winner_tps else ""
                    parts.append(f"  TPS {_fmt(r.mean_tps)}{w} | TTFT {format_ms(r.mean_ttft_ms)} | TPOT {_fmt(r.mean_tpot_ms, 0)}ms")
                elif r.mode == BenchmarkMode.TOOL_CALLING:
                    w = " [bold yellow]★[/bold yellow]" if r.winner_tool_accuracy else ""
                    parts.append(f"  Tool name {_pct(r.tool_name_accuracy)}{w} | args {_fmt(r.mean_tool_args_score, 2)}")
                elif r.mode == BenchmarkMode.PARALLEL:
                    w = " [bold yellow]★[/bold yellow]" if r.winner_tps else ""
                    parts.append(f"  Parallel TPS {_fmt(r.parallel_tps)}{w}")
            lines.append("\n".join(parts))

        self.query_one("#summary-content", Static).update("\n\n".join(lines))

    def _export_results(self) -> None:
        if not self._results:
            self.notify("No results to export", severity="warning")
            return
        self._do_export(list(self._results))

    @work
    async def _do_export(self, results: list) -> None:
        from ..benchmark.export import ReportExporter
        import pathlib
        export_dir = pathlib.Path(self.app.config.benchmark.export_dir).expanduser()
        ts = time.strftime("%Y%m%d-%H%M%S")
        exporter = ReportExporter(export_dir)
        exporter.export_all(results, f"benchmark-{ts}")
        self.notify(f"Exported to {export_dir}", severity="information")
