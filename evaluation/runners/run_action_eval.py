"""Run local Action/Voice gold-sample evaluation."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from evaluation.common import append_jsonl, collect_manifest, load_jsonl, new_run_dir, write_json
from evaluation.scorers.action_metrics import score_action_records
from hai_avatar.app import build_pipeline
from hai_avatar.config import load_settings


async def main_async() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="evaluation/datasets/action_gold.jsonl")
    parser.add_argument("--provider", default="mock", choices=["mock", "openai"])
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--output")
    args = parser.parse_args()

    run_dir = new_run_dir("action", args.output)
    settings = load_settings()
    settings.llm.provider = args.provider
    settings.tts.provider = "mock"
    samples = load_jsonl(Path(args.dataset))
    if args.limit:
        samples = samples[: args.limit]
    collect_manifest(Path(args.dataset), run_dir, {"runner": "run_action_eval", "provider": args.provider})

    records = []
    for sample in samples:
        pipeline = build_pipeline(settings)
        result = await pipeline.process(sample["user_text"], user_id=sample["sample_id"])
        record = {
            "sample_id": sample["sample_id"],
            "user_text": sample["user_text"],
            "gold": {"acceptable": sample["acceptable"], "forbidden": sample.get("forbidden", {})},
            "result": result.model_dump(mode="json"),
        }
        records.append(record)
    append_jsonl(run_dir / "outputs.jsonl", records)
    metrics = score_action_records(records)
    write_json(run_dir / "metrics.json", metrics)
    print(f"Wrote {len(records)} records to {run_dir}")
    print(metrics)


if __name__ == "__main__":
    asyncio.run(main_async())
