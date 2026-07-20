"""Run InCharacter BFI official-questionnaire adapted evaluation."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from evaluation.common import append_jsonl, collect_manifest, load_json, load_jsonl, new_run_dir, write_json
from evaluation.scorers.incharacter_metrics import score_incharacter_records
from hai_avatar.app import build_pipeline
from hai_avatar.config import load_settings


async def main_async() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="evaluation/datasets/official_adapted/incharacter_bfi_official_subset.jsonl")
    parser.add_argument("--source-metadata", default="evaluation/datasets/official_adapted/source_metadata.json")
    parser.add_argument("--provider", default="mock", choices=["mock", "openai"])
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--output")
    parser.add_argument("--enable-personalization", action="store_true")
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    run_dir = new_run_dir("incharacter_bfi_adapted", args.output)
    settings = load_settings()
    settings.llm.provider = args.provider
    settings.tts.provider = "mock"
    settings.avatar.provider = "mock"
    settings.personalization.enabled = args.enable_personalization
    settings.planner.enable_cooldown = False
    settings.app.max_input_chars = 3000
    samples = load_jsonl(dataset_path)
    if args.limit:
        samples = samples[: args.limit]
    metadata_path = Path(args.source_metadata)
    source_metadata = load_json(metadata_path) if metadata_path.exists() else {}
    collect_manifest(
        dataset_path,
        run_dir,
        {
            "runner": "run_incharacter_bfi_adapted",
            "provider": args.provider,
            "benchmark": "InCharacter",
            "source_metadata": source_metadata.get("InCharacter", {}),
            "reporting_boundary": "InCharacter-inspired adapted BFI interview; not official InCharacter score.",
        },
    )

    records = []
    pipeline = build_pipeline(settings)
    for sample in samples:
        result = await pipeline.process(sample["user_text"], user_id="avatar_persona_hai_companion")
        records.append({"sample": sample, "result": result.model_dump(mode="json")})
    append_jsonl(run_dir / "outputs.jsonl", records)
    metrics = score_incharacter_records(records)
    write_json(run_dir / "metrics.json", metrics)
    print(f"Wrote {len(records)} records to {run_dir}")
    print(metrics)


if __name__ == "__main__":
    asyncio.run(main_async())
