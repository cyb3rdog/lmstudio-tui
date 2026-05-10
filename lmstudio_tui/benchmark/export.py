from __future__ import annotations

import csv
import json
from pathlib import Path

from .analysis import BenchmarkResult


def _f(v: float | None, decimals: int = 1) -> str:
    return f"{v:.{decimals}f}" if v is not None else "—"


def _pct(v: float | None) -> str:
    return f"{v * 100:.1f}%" if v is not None else "—"


class ReportExporter:
    def __init__(self, output_dir: Path | str) -> None:
        self._dir = Path(output_dir).expanduser()
        self._dir.mkdir(parents=True, exist_ok=True)

    def export_all(self, results: list[BenchmarkResult], basename: str) -> dict[str, Path]:
        return {
            "json": self.export_json(results, f"{basename}.json"),
            "csv": self.export_csv(results, f"{basename}.csv"),
            "md": self.export_markdown(results, f"{basename}.md"),
        }

    def export_json(self, results: list[BenchmarkResult], filename: str) -> Path:
        path = self._dir / filename
        serialized = []
        for r in results:
            d = {
                "model_id": r.model_id,
                "server_name": r.server_name,
                "mode": r.mode,
                "runs": r.runs,
                "winners": {
                    "tps": r.winner_tps,
                    "ttft": r.winner_ttft,
                    "tool_accuracy": r.winner_tool_accuracy,
                    "load_time": r.winner_load_time,
                },
                "tps": {
                    "mean": r.mean_tps, "median": r.median_tps,
                    "p95": r.p95_tps, "p99": r.p99_tps,
                    "stdev": r.stdev_tps, "min": r.min_tps, "max": r.max_tps,
                },
                "ttft_ms": {
                    "mean": r.mean_ttft_ms, "median": r.median_ttft_ms,
                    "p95": r.p95_ttft_ms, "p99": r.p99_ttft_ms,
                    "stdev": r.stdev_ttft_ms,
                },
                "tpot_ms": {"mean": r.mean_tpot_ms, "median": r.median_tpot_ms},
                "total_ms": {"mean": r.mean_total_ms, "p95": r.p95_total_ms},
                "tokens": {
                    "avg_prompt": r.avg_prompt_tokens,
                    "avg_completion": r.avg_completion_tokens,
                    "avg_reasoning": r.avg_reasoning_tokens,
                },
                "tool_calling": {
                    "tool_call_rate": r.tool_call_rate,
                    "tool_name_accuracy": r.tool_name_accuracy,
                    "mean_tool_args_score": r.mean_tool_args_score,
                },
                "load_time_ms": {"mean": r.mean_load_time_ms, "p95": r.p95_load_time_ms},
                "jit_detected": r.jit_detected,
                "parallel_tps": r.parallel_tps,
                "samples": [
                    {
                        "model_id": s.model_id,
                        "tokens_per_second": s.tokens_per_second,
                        "time_to_first_token_ms": s.time_to_first_token_ms,
                        "tpot_ms": s.tpot_ms,
                        "total_duration_ms": s.total_duration_ms,
                        "prompt_tokens": s.prompt_tokens,
                        "completion_tokens": s.completion_tokens,
                        "reasoning_tokens": s.reasoning_tokens,
                        "tool_called": s.tool_called,
                        "tool_name_correct": s.tool_name_correct,
                        "tool_args_score": s.tool_args_score,
                        "load_time_ms": s.load_time_ms,
                        "was_jit": s.was_jit,
                    }
                    for s in r.raw_samples
                ],
            }
            serialized.append(d)
        path.write_text(json.dumps(serialized, indent=2))
        return path

    def export_csv(self, results: list[BenchmarkResult], filename: str) -> Path:
        path = self._dir / filename
        all_rows = []
        for r in results:
            for s in r.raw_samples:
                all_rows.append({
                    "model_id": s.model_id,
                    "server": r.server_name,
                    "mode": r.mode,
                    "tokens_per_second": s.tokens_per_second,
                    "ttft_ms": s.time_to_first_token_ms,
                    "tpot_ms": s.tpot_ms,
                    "total_ms": s.total_duration_ms,
                    "prompt_tokens": s.prompt_tokens,
                    "completion_tokens": s.completion_tokens,
                    "reasoning_tokens": s.reasoning_tokens,
                    "tool_called": s.tool_called,
                    "tool_name_correct": s.tool_name_correct,
                    "tool_args_score": s.tool_args_score,
                    "load_time_ms": s.load_time_ms,
                    "was_jit": s.was_jit,
                })
        if not all_rows:
            return path
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
            writer.writeheader()
            writer.writerows(all_rows)
        return path

    def export_markdown(self, results: list[BenchmarkResult], filename: str) -> Path:
        path = self._dir / filename
        lines: list[str] = ["# LM Studio Benchmark Report", ""]

        # Group by mode
        modes = dict.fromkeys(r.mode for r in results)
        for mode in modes:
            mode_results = [r for r in results if r.mode == mode]
            lines.append(f"## Mode: {mode.replace('_', ' ').title()}")
            lines.append("")
            self._md_section(mode, mode_results, lines)
            lines.append("")

        path.write_text("\n".join(lines) + "\n")
        return path

    def _md_section(self, mode: str, results: list[BenchmarkResult], lines: list[str]) -> None:
        if mode == "throughput":
            lines.append("| Model | Runs | Mean TPS ★ | p95 TPS | TTFT p50 | TPOT p50 | Avg out |")
            lines.append("|-------|------|-----------|---------|----------|----------|---------|")
            for r in results:
                w_tps = " ★" if r.winner_tps else ""
                w_ttft = " ★" if r.winner_ttft else ""
                lines.append(
                    f"| {r.model_id} | {r.runs}"
                    f" | {_f(r.mean_tps)}{w_tps}"
                    f" | {_f(r.p95_tps)}"
                    f" | {_f(r.median_ttft_ms)}ms{w_ttft}"
                    f" | {_f(r.median_tpot_ms)}ms"
                    f" | {_f(r.avg_completion_tokens, 0)} |"
                )

        elif mode == "tool_calling":
            lines.append("| Model | Runs | Call Rate | Name Acc ★ | Arg Score | TTFT p50 |")
            lines.append("|-------|------|-----------|-----------|-----------|----------|")
            for r in results:
                w_tool = " ★" if r.winner_tool_accuracy else ""
                lines.append(
                    f"| {r.model_id} | {r.runs}"
                    f" | {_pct(r.tool_call_rate)}"
                    f" | {_pct(r.tool_name_accuracy)}{w_tool}"
                    f" | {_f(r.mean_tool_args_score, 2)}"
                    f" | {_f(r.median_ttft_ms)}ms |"
                )

        elif mode == "load_time":
            lines.append("| Model | Runs | Mean Load ★ | p95 Load | JIT? |")
            lines.append("|-------|------|------------|---------|------|")
            for r in results:
                w_load = " ★" if r.winner_load_time else ""
                jit = "Yes" if r.jit_detected else "No"
                lines.append(
                    f"| {r.model_id} | {r.runs}"
                    f" | {_f(r.mean_load_time_ms, 0)}ms{w_load}"
                    f" | {_f(r.p95_load_time_ms, 0)}ms"
                    f" | {jit} |"
                )

        elif mode == "parallel":
            lines.append("| Model | Slots | Total Req | Agg TPS ★ | p50 TTFT/req | p95 TTFT/req |")
            lines.append("|-------|-------|-----------|----------|-------------|-------------|")
            for r in results:
                w_tps = " ★" if r.winner_tps else ""
                lines.append(
                    f"| {r.model_id} | — | {r.runs}"
                    f" | {_f(r.parallel_tps)}{w_tps}"
                    f" | {_f(r.median_ttft_ms)}ms"
                    f" | {_f(r.p95_ttft_ms)}ms |"
                )
