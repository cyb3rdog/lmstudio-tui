from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path

from .analysis import BenchmarkResult


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
                "runs": r.runs,
                "tps": {"mean": r.mean_tps, "median": r.median_tps, "p95": r.p95_tps,
                         "p99": r.p99_tps, "stdev": r.stdev_tps, "min": r.min_tps, "max": r.max_tps},
                "ttft_ms": {"mean": r.mean_ttft_ms, "median": r.median_ttft_ms,
                            "p95": r.p95_ttft_ms, "p99": r.p99_ttft_ms, "stdev": r.stdev_ttft_ms},
                "total_ms": {"mean": r.mean_total_ms, "p95": r.p95_total_ms},
                "avg_tokens": {"prompt": r.avg_prompt_tokens, "completion": r.avg_completion_tokens},
                "samples": [
                    {
                        "model_id": s.model_id,
                        "tokens_per_second": s.tokens_per_second,
                        "time_to_first_token_ms": s.time_to_first_token_ms,
                        "total_duration_ms": s.total_duration_ms,
                        "prompt_tokens": s.prompt_tokens,
                        "completion_tokens": s.completion_tokens,
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
                    "tokens_per_second": s.tokens_per_second,
                    "ttft_ms": s.time_to_first_token_ms,
                    "total_ms": s.total_duration_ms,
                    "prompt_tokens": s.prompt_tokens,
                    "completion_tokens": s.completion_tokens,
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
        lines = ["# LM Studio Benchmark Report", ""]
        lines.append("| Model | Runs | Mean TPS | p95 TPS | Mean TTFT | p95 TTFT | Avg tokens |")
        lines.append("|-------|------|----------|---------|-----------|----------|------------|")
        for r in results:
            def _f(v): return f"{v:.1f}" if v is not None else "—"
            lines.append(
                f"| {r.model_id} | {r.runs} "
                f"| {_f(r.mean_tps)} | {_f(r.p95_tps)} "
                f"| {_f(r.mean_ttft_ms)}ms | {_f(r.p95_ttft_ms)}ms "
                f"| {_f(r.avg_prompt_tokens)}/{_f(r.avg_completion_tokens)} |"
            )
        path.write_text("\n".join(lines) + "\n")
        return path
