"""Run CharacterEval-derived local dialogue smoke evaluation."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from evaluation.common import append_jsonl, collect_manifest, load_jsonl, new_run_dir, write_json
from evaluation.scorers.dialogue_metrics import score_dialogue_records
from hai_avatar.app import build_pipeline
from hai_avatar.config import load_settings


async def main_async() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="evaluation/datasets/character_eval_subset.jsonl")
    parser.add_argument("--provider", default="mock", choices=["mock", "openai"])
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--output")
    args = parser.parse_args()

    run_dir = new_run_dir("character_subset", args.output)
    settings = load_settings()
    settings.llm.provider = args.provider
    settings.tts.provider = "mock"
    samples = load_jsonl(Path(args.dataset))
    if args.limit:
        samples = samples[: args.limit]
    collect_manifest(Path(args.dataset), run_dir, {"runner": "run_character_eval_subset", "provider": args.provider})

    records = []
    for sample in samples:
        pipeline = build_pipeline(settings)
        session_id = sample["sample_id"]
        for user_text, assistant_text in sample.get("history", []):
            pipeline.conversation_service.add_turn(session_id, user_text, assistant_text)
        result = await pipeline.process(sample["user_text"], user_id=session_id)
        records.append({"sample": sample, "result": result.model_dump(mode="json")})
    append_jsonl(run_dir / "outputs.jsonl", records)
    metrics = score_dialogue_records(records)
    write_json(run_dir / "metrics.json", metrics)
    print(f"Wrote {len(records)} records to {run_dir}")
    print(metrics)


if __name__ == "__main__":
    asyncio.run(main_async())
