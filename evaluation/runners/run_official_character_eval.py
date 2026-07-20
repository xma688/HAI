"""Run CharacterEval official-data adapted evaluation."""

from __future__ import annotations

import argparse
import asyncio
import copy
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from evaluation.common import append_jsonl, collect_manifest, load_json, load_jsonl, new_run_dir, write_json
from evaluation.scorers.dialogue_metrics import score_dialogue_records
from hai_avatar.app import build_pipeline
from hai_avatar.config import load_settings


async def main_async() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="evaluation/datasets/official_adapted/charactereval_official_subset.jsonl")
    parser.add_argument("--source-metadata", default="evaluation/datasets/official_adapted/source_metadata.json")
    parser.add_argument("--provider", default="mock", choices=["mock", "openai"])
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--output")
    parser.add_argument("--enable-personalization", action="store_true")
    parser.add_argument("--write-official-format", action="store_true", default=True)
    parser.add_argument(
        "--allow-external-data-export",
        action="store_true",
        help="Required with --provider openai because CharacterEval samples include benchmark contexts and character profiles.",
    )
    args = parser.parse_args()
    if args.provider == "openai" and not args.allow_external_data_export:
        raise SystemExit(
            "Refusing to send CharacterEval contexts/profiles to an external API without "
            "--allow-external-data-export."
        )

    dataset_path = Path(args.dataset)
    run_dir = new_run_dir("charactereval_official_adapted", args.output)
    settings = load_settings()
    settings.llm.provider = args.provider
    settings.tts.provider = "mock"
    settings.avatar.provider = "mock"
    settings.personalization.enabled = args.enable_personalization
    settings.planner.enable_cooldown = False
    settings.app.max_input_chars = 4000
    samples = load_jsonl(dataset_path)
    if args.limit:
        samples = samples[: args.limit]
    metadata_path = Path(args.source_metadata)
    source_metadata = load_json(metadata_path) if metadata_path.exists() else {}
    collect_manifest(
        dataset_path,
        run_dir,
        {
            "runner": "run_official_character_eval",
            "provider": args.provider,
            "benchmark": "CharacterEval",
            "source_metadata": source_metadata.get("CharacterEval", {}),
            "external_data_export_ack": bool(args.allow_external_data_export),
            "reporting_boundary": "Adapted local HAI run; not official CharacterEval/CharacterRM score.",
        },
    )

    records = []
    for sample in samples:
        pipeline = build_pipeline(settings)
        result = await pipeline.process(sample["user_text"], user_id=sample["sample_id"])
        records.append({"sample": sample, "result": result.model_dump(mode="json")})
    append_jsonl(run_dir / "outputs.jsonl", records)
    write_official_format(run_dir, records)
    metrics = score_dialogue_records(records)
    metrics["metric_tag_coverage"] = _metric_tag_coverage(records)
    metrics["charrm_status"] = "not_run; use CharacterEval BaichuanCharRM weights to produce official reward-model scores"
    metrics["reporting_boundary"] = "CharacterEval-adapted dialogue metrics; not official CharacterRM score."
    write_json(run_dir / "metrics.json", metrics)
    print(f"Wrote {len(records)} records to {run_dir}")
    print(metrics)


def _metric_tag_coverage(records: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        for tag in record["sample"].get("metric_tags", []):
            key = tag.get("metric_en", "unknown")
            counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def write_official_format(run_dir: Path, records: list[dict]) -> None:
    generation_records = []
    transformed_records = []
    for record in records:
        sample = record["sample"]
        result = record["result"]
        generation = {
            "id": sample["source_id"],
            "role": sample["role"],
            "novel_name": sample.get("novel_name", ""),
            "context": sample["context"],
            "model_output": result["reply_text"].splitlines()[0],
            "hai_avatar_command": result["avatar_command"],
            "hai_warnings": result.get("warnings", []),
        }
        generation_records.append(generation)
        for tag in sample.get("metric_tags", []):
            transformed = copy.deepcopy(generation)
            transformed["metric_en"] = tag["metric_en"]
            transformed["metric_zh"] = tag["metric_zh"]
            transformed_records.append(transformed)

    (run_dir / "generation.json").write_text(
        json.dumps(generation_records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (run_dir / "generation_trans.json").write_text(
        json.dumps(transformed_records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    asyncio.run(main_async())
