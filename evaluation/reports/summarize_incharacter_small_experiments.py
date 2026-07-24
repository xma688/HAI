"""Summarize small InCharacter follow-up experiments."""

from __future__ import annotations

import argparse
import csv
import html
import json
from pathlib import Path
from statistics import mean, stdev
from typing import Any

import matplotlib.pyplot as plt


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def mean_std(values: list[float]) -> dict[str, float | int | None]:
    return {
        "n": len(values),
        "mean": round(mean(values), 4) if values else None,
        "std": round(stdev(values), 4) if len(values) > 1 else 0.0 if values else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bfi-runs", nargs="+", required=True)
    parser.add_argument("--empathy-run", required=True)
    parser.add_argument("--control-run", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    bfi_metrics = [load_json(Path(run) / "metrics.json") for run in args.bfi_runs]
    empathy_metrics = load_json(Path(args.empathy_run) / "metrics.json")
    control_metrics = load_json(Path(args.control_run) / "metrics.json")

    summary = {
        "bfi_repeats": summarize_bfi_repeats(bfi_metrics),
        "empathy": summarize_single_run(empathy_metrics),
        "ablation": summarize_ablation(control_metrics, bfi_metrics[0]),
        "inputs": {
            "bfi_runs": args.bfi_runs,
            "empathy_run": args.empathy_run,
            "control_run": args.control_run,
        },
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(out_dir / "summary.csv", summary)
    chart_paths = write_charts(out_dir, summary)
    write_html(out_dir / "incharacter_small_experiments.html", summary, chart_paths)
    print(f"Wrote summary to {out_dir / 'incharacter_small_experiments.html'}")


def summarize_bfi_repeats(runs: list[dict[str, Any]]) -> dict[str, Any]:
    personas = sorted(runs[0]["per_persona"])
    persona_summary = {}
    for persona in personas:
        macro_mae = [run["per_persona"][persona]["macro_mae"] for run in runs]
        direction = [run["per_persona"][persona]["direction_accuracy"] for run in runs]
        persona_summary[persona] = {
            "macro_mae": mean_std(macro_mae),
            "direction_accuracy": mean_std(direction),
        }
    return {
        "repeat_count": len(runs),
        "record_count_total": sum(run["count"] for run in runs),
        "aggregate_macro_mae": mean_std([run["aggregate_macro_mae"] for run in runs]),
        "aggregate_direction_accuracy": mean_std([run["aggregate_direction_accuracy"] for run in runs]),
        "per_persona": persona_summary,
    }


def summarize_single_run(metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        "count": metrics["count"],
        "aggregate_macro_mae": metrics["aggregate_macro_mae"],
        "aggregate_direction_accuracy": metrics["aggregate_direction_accuracy"],
        "per_persona": {
            persona: {
                "macro_mae": payload["macro_mae"],
                "direction_accuracy": payload["direction_accuracy"],
                "dimension_scores": payload["dimension_scores"],
            }
            for persona, payload in metrics["per_persona"].items()
        },
    }


def summarize_ablation(control: dict[str, Any], multi: dict[str, Any]) -> dict[str, Any]:
    supportive = multi["per_persona"]["supportive"]
    return {
        "control_no_persona": {
            "count": control["count"],
            "macro_mae": control["aggregate_macro_mae"],
            "dimension_scores": control["per_persona"]["control"]["dimension_scores"],
        },
        "single_supportive": {
            "count": supportive["count"],
            "macro_mae": supportive["macro_mae"],
            "dimension_scores": supportive["dimension_scores"],
        },
        "multi_persona": {
            "count": multi["count"],
            "macro_mae": multi["aggregate_macro_mae"],
            "persona_count": multi["persona_count"],
        },
    }


def write_csv(path: Path, summary: dict[str, Any]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["experiment", "group", "metric", "value", "std", "n"])
        writer.writerow(
            [
                "bfi_repeats",
                "aggregate",
                "macro_mae",
                summary["bfi_repeats"]["aggregate_macro_mae"]["mean"],
                summary["bfi_repeats"]["aggregate_macro_mae"]["std"],
                summary["bfi_repeats"]["aggregate_macro_mae"]["n"],
            ]
        )
        for persona, metrics in summary["bfi_repeats"]["per_persona"].items():
            writer.writerow(
                [
                    "bfi_repeats",
                    persona,
                    "macro_mae",
                    metrics["macro_mae"]["mean"],
                    metrics["macro_mae"]["std"],
                    metrics["macro_mae"]["n"],
                ]
            )
        writer.writerow(["empathy", "aggregate", "macro_mae", summary["empathy"]["aggregate_macro_mae"], "", ""])
        for persona, metrics in summary["empathy"]["per_persona"].items():
            writer.writerow(["empathy", persona, "macro_mae", metrics["macro_mae"], "", ""])
        for group, metrics in summary["ablation"].items():
            writer.writerow(["ablation", group, "macro_mae", metrics["macro_mae"], "", metrics["count"]])


def write_charts(out_dir: Path, summary: dict[str, Any]) -> list[Path]:
    chart_paths = []
    path = out_dir / "bfi_repeat_macro_mae.png"
    labels = list(summary["bfi_repeats"]["per_persona"])
    values = [summary["bfi_repeats"]["per_persona"][label]["macro_mae"]["mean"] for label in labels]
    errors = [summary["bfi_repeats"]["per_persona"][label]["macro_mae"]["std"] for label in labels]
    plt.figure(figsize=(7.5, 4.4))
    plt.bar(labels, values, yerr=errors, capsize=5)
    plt.ylabel("Macro MAE")
    plt.title("BFI Repeat Stability")
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()
    chart_paths.append(path)

    path = out_dir / "empathy_macro_mae.png"
    labels = list(summary["empathy"]["per_persona"])
    values = [summary["empathy"]["per_persona"][label]["macro_mae"] for label in labels]
    plt.figure(figsize=(7.5, 4.4))
    plt.bar(labels, values)
    plt.ylabel("Macro MAE")
    plt.title("Empathy Questionnaire")
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()
    chart_paths.append(path)

    path = out_dir / "ablation_macro_mae.png"
    labels = list(summary["ablation"])
    values = [summary["ablation"][label]["macro_mae"] for label in labels]
    plt.figure(figsize=(8.5, 4.4))
    plt.bar(labels, values)
    plt.ylabel("Macro MAE")
    plt.title("Persona Ablation")
    plt.xticks(rotation=15, ha="right")
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()
    chart_paths.append(path)
    return chart_paths


def write_html(path: Path, summary: dict[str, Any], chart_paths: list[Path]) -> None:
    rows = []
    for section, payload in summary.items():
        rows.append(
            f"<h2>{html.escape(section)}</h2><pre>{html.escape(json.dumps(payload, ensure_ascii=False, indent=2))}</pre>"
        )
    images = "".join(
        f'<figure><img src="{chart.name}" alt="{chart.name}"><figcaption>{chart.name}</figcaption></figure>'
        for chart in chart_paths
    )
    path.write_text(
        f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>InCharacter Small Experiments</title>
  <style>
    body {{ font-family: Arial, "Microsoft YaHei", sans-serif; margin: 32px; color: #1f2937; }}
    pre {{ white-space: pre-wrap; background: #f9fafb; border: 1px solid #e5e7eb; padding: 12px; border-radius: 8px; }}
    img {{ max-width: 760px; width: 100%; border: 1px solid #e5e7eb; border-radius: 8px; }}
  </style>
</head>
<body>
  <h1>InCharacter Small Experiments</h1>
  {images}
  {''.join(rows)}
</body>
</html>
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
