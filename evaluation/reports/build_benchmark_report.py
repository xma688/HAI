"""Build a compact HTML report for HAI benchmark runs."""

from __future__ import annotations

import argparse
import csv
import html
import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", nargs="+", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    run_summaries = []
    for run in args.runs:
        run_dir = Path(run)
        metrics_path = run_dir / "metrics.json"
        manifest_path = run_dir / "manifest.json"
        if not metrics_path.exists():
            continue
        metrics = load_json(metrics_path)
        charrm_path = run_dir / "charrm_metrics.json"
        if charrm_path.exists():
            metrics["character_rm"] = load_json(charrm_path)
        run_summaries.append(
            {
                "run_dir": run_dir,
                "metrics": metrics,
                "manifest": load_json(manifest_path) if manifest_path.exists() else {},
            }
        )

    write_csv(out_dir / "metrics_summary.csv", run_summaries)
    chart_paths = write_charts(out_dir, run_summaries)
    write_html(out_dir / "benchmark_report.html", run_summaries, chart_paths)
    print(f"Wrote report to {out_dir / 'benchmark_report.html'}")


def write_csv(path: Path, summaries: list[dict[str, Any]]) -> None:
    fieldnames = [
        "run",
        "benchmark",
        "provider",
        "count",
        "macro_mae",
        "direction_accuracy",
        "fluency_proxy",
        "coherency_proxy",
        "empathy_proxy",
        "warning_rate",
        "llm_fallback_rate",
        "character_rm_scores",
        "boundary",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for summary in summaries:
            metrics = summary["metrics"]
            manifest = summary["manifest"]
            writer.writerow(
                {
                    "run": summary["run_dir"].name,
                    "benchmark": manifest.get("benchmark", manifest.get("runner", "")),
                    "provider": manifest.get("provider", ""),
                    "count": metrics.get("count", ""),
                    "macro_mae": metrics.get("macro_mae", ""),
                    "direction_accuracy": metrics.get("direction_accuracy", ""),
                    "fluency_proxy": metrics.get("fluency_proxy", ""),
                    "coherency_proxy": metrics.get("coherency_proxy", ""),
                    "empathy_proxy": metrics.get("empathy_proxy", ""),
                    "warning_rate": metrics.get("warning_rate", ""),
                    "llm_fallback_rate": metrics.get("llm_fallback_rate", ""),
                    "character_rm_scores": json.dumps(
                        metrics.get("character_rm", {}).get("scores", {}),
                        ensure_ascii=False,
                    ),
                    "boundary": metrics.get("reporting_boundary", manifest.get("reporting_boundary", "")),
                }
            )


def write_charts(out_dir: Path, summaries: list[dict[str, Any]]) -> list[Path]:
    chart_paths: list[Path] = []
    for summary in summaries:
        metrics = summary["metrics"]
        run_name = summary["run_dir"].name
        if "dimension_scores" in metrics:
            path = out_dir / f"{run_name}_bfi.png"
            labels = list(metrics["dimension_scores"].keys())
            predicted = [metrics["dimension_scores"][label]["predicted_bfi_1_to_5"] or 0 for label in labels]
            target = [metrics["dimension_scores"][label]["target_bfi_1_to_5"] for label in labels]
            x = range(len(labels))
            plt.figure(figsize=(9, 4.8))
            plt.bar([i - 0.18 for i in x], predicted, width=0.36, label="Predicted")
            plt.bar([i + 0.18 for i in x], target, width=0.36, label="Target")
            plt.xticks(list(x), labels, rotation=20, ha="right")
            plt.ylim(1, 5)
            plt.ylabel("BFI score")
            plt.title("InCharacter BFI Self-Report")
            plt.legend()
            plt.tight_layout()
            plt.savefig(path, dpi=160)
            plt.close()
            chart_paths.append(path)
        elif any(key in metrics for key in ["fluency_proxy", "coherency_proxy", "empathy_proxy"]):
            path = out_dir / f"{run_name}_dialogue.png"
            labels = ["fluency", "coherency", "empathy", "diversity"]
            values = [
                metrics.get("fluency_proxy", 0),
                metrics.get("coherency_proxy", 0),
                metrics.get("empathy_proxy", 0),
                metrics.get("expression_diversity_proxy", 0),
            ]
            plt.figure(figsize=(7.5, 4.4))
            plt.bar(labels, values, color=["#2563eb", "#16a34a", "#f97316", "#7c3aed"])
            plt.ylim(0, 1)
            plt.ylabel("proxy score")
            plt.title("CharacterEval-Adapted Dialogue Metrics")
            plt.tight_layout()
            plt.savefig(path, dpi=160)
            plt.close()
            chart_paths.append(path)
        if metrics.get("character_rm", {}).get("scores"):
            path = out_dir / f"{run_name}_charrm.png"
            scores = metrics["character_rm"]["scores"]
            labels = list(scores.keys())
            values = [scores[label] for label in labels]
            plt.figure(figsize=(7.5, 4.4))
            plt.bar(labels, values, color=["#2563eb", "#16a34a", "#f97316", "#7c3aed"][: len(labels)])
            plt.ylim(1, 5)
            plt.ylabel("CharacterRM score")
            plt.title("CharacterEval CharacterRM")
            plt.tight_layout()
            plt.savefig(path, dpi=160)
            plt.close()
            chart_paths.append(path)
    return chart_paths


def write_html(path: Path, summaries: list[dict[str, Any]], chart_paths: list[Path]) -> None:
    sections = []
    for summary in summaries:
        metrics = summary["metrics"]
        manifest = summary["manifest"]
        rows = "".join(
            f"<tr><th>{html.escape(str(key))}</th><td><code>{html.escape(json.dumps(value, ensure_ascii=False))}</code></td></tr>"
            for key, value in metrics.items()
            if key not in {"dimension_scores", "per_dimension"}
        )
        sections.append(
            f"""
            <section>
              <h2>{html.escape(summary['run_dir'].name)}</h2>
              <p><b>Benchmark:</b> {html.escape(str(manifest.get('benchmark', manifest.get('runner', 'unknown'))))}
                 <b>Provider:</b> {html.escape(str(manifest.get('provider', '')))}</p>
              <table>{rows}</table>
            </section>
            """
        )
    images = "\n".join(
        f'<figure><img src="{html.escape(chart.name)}" alt="{html.escape(chart.name)}"><figcaption>{html.escape(chart.name)}</figcaption></figure>'
        for chart in chart_paths
    )
    path.write_text(
        f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>HAI Benchmark Report</title>
  <style>
    body {{ font-family: Arial, "Microsoft YaHei", sans-serif; margin: 32px; color: #1f2937; }}
    h1, h2 {{ color: #111827; }}
    section {{ margin: 24px 0; padding: 18px; border: 1px solid #d1d5db; border-radius: 8px; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border-bottom: 1px solid #e5e7eb; padding: 8px; text-align: left; vertical-align: top; }}
    th {{ width: 220px; color: #374151; }}
    code {{ white-space: pre-wrap; word-break: break-word; }}
    img {{ max-width: 760px; width: 100%; border: 1px solid #e5e7eb; border-radius: 8px; }}
    .note {{ padding: 12px; background: #fff7ed; border: 1px solid #fed7aa; border-radius: 8px; }}
  </style>
</head>
<body>
  <h1>HAI Benchmark Report</h1>
  <p class="note">InCharacter self-report uses official BFI scoring rules. CharacterEval output is converted to official generation/generation_trans format; official CharacterRM scoring requires local BaichuanCharRM weights.</p>
  {''.join(sections)}
  <h2>Charts</h2>
  {images}
</body>
</html>
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
