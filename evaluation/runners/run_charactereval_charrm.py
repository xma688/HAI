"""Run CharacterEval's BaichuanCharRM scorer on generated official-format data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import torch


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--character-profiles", default=".tmp/CharacterEval/data/character_profiles.json")
    parser.add_argument("--reward-model-path", required=True)
    parser.add_argument("--max-seq-length", type=int, default=4096)
    parser.add_argument(
        "--max-records-per-metric",
        type=int,
        default=0,
        help="Optional balanced CharacterRM sample size per metric. 0 scores every transformed record.",
    )
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    reward_model_path = Path(args.reward_model_path)
    if not reward_model_path.exists():
        raise SystemExit(
            f"Missing CharacterRM model path: {reward_model_path}. "
            "Download morecry/BaichuanCharRM locally, then rerun."
        )
    generation_trans_path = run_dir / "generation_trans.json"
    if not generation_trans_path.exists():
        raise SystemExit(f"Missing {generation_trans_path}; run run_official_character_eval.py first.")

    sys.path.insert(0, str(reward_model_path.parent))
    from BaichuanCharRM.modeling_baichuan import BaichuanCharRM
    from BaichuanCharRM.tokenization_baichuan import BaichuanTokenizer

    character_profile = load_json(Path(args.character_profiles))
    all_records = load_json(generation_trans_path)
    records = select_records(all_records, args.max_records_per_metric)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.bfloat16 if device == "cuda" else torch.float32

    tokenizer = BaichuanTokenizer.from_pretrained(str(reward_model_path))
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "left"
    model = BaichuanCharRM.from_pretrained(str(reward_model_path), torch_dtype=dtype).to(device)
    model.eval()

    for record in records:
        input_text = format_input(record, character_profile)
        input_ids = tokenizer.encode(text=input_text, add_special_tokens=False) + [tokenizer.eos_token_id]
        if len(input_ids) > args.max_seq_length:
            input_ids = input_ids[-args.max_seq_length :]
        tensor = torch.tensor(input_ids, device=device).unsqueeze(0)
        with torch.no_grad():
            score = model(input_ids=tensor)[1].item() * 4 + 1
        record[record["metric_en"]] = score

    (run_dir / "charrm_evaluation.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    metrics: dict[str, list[float]] = {}
    for record in records:
        metric = record["metric_en"]
        metrics.setdefault(metric, []).append(float(record[metric]))
    summary = {
        "count": len(records),
        "available_count": len(all_records),
        "max_records_per_metric": args.max_records_per_metric,
        "device": device,
        "scores": {metric: round(sum(values) / len(values), 4) for metric, values in sorted(metrics.items())},
        "reporting_boundary": "Official CharacterEval CharacterRM scores for the generated adapted HAI responses.",
    }
    (run_dir / "charrm_metrics.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(summary)


def select_records(records: list[dict[str, Any]], max_records_per_metric: int) -> list[dict[str, Any]]:
    if max_records_per_metric <= 0:
        return records
    counts: dict[str, int] = {}
    selected: list[dict[str, Any]] = []
    for record in records:
        metric = record["metric_en"]
        if counts.get(metric, 0) >= max_records_per_metric:
            continue
        selected.append(record)
        counts[metric] = counts.get(metric, 0) + 1
    return selected


def format_input(example: dict[str, Any], character_profile: dict[str, Any]) -> str:
    return (
        "<RoleInfo>\n\n"
        + str(character_profile[example["role"]])
        + "\n\n<Context>\n\n"
        + example["context"]
        + "\n\n<Response>\n\n"
        + example["model_output"]
        + "\n\n<Dimension>\n\n"
        + example["metric_zh"]
    )


if __name__ == "__main__":
    main()
