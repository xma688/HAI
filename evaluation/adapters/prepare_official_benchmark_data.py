"""Prepare adapted official benchmark subsets for local HAI evaluation.

The generated datasets use public data from:
- CharacterEval: https://github.com/morecry/CharacterEval
- InCharacter: https://github.com/Neph0s/InCharacter

They are adapted to HAI's chat-avatar pipeline and must not be reported as
complete official benchmark scores.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from collections import Counter
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CHARACTER_EVAL_ROOT = PROJECT_ROOT / ".tmp" / "CharacterEval"
DEFAULT_INCHARACTER_ROOT = PROJECT_ROOT / ".tmp" / "InCharacter"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "evaluation" / "datasets" / "official_adapted"


AVATAR_PERSONA = {
    "name": "HAI Companion",
    "description": "patient, supportive, non-judgmental Chinese conversational avatar",
    "big_five": {
        "openness": 0.65,
        "conscientiousness": 0.70,
        "extraversion": 0.55,
        "agreeableness": 0.85,
        "neuroticism": 0.20,
    },
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def compact_profile(profile: dict[str, Any], max_chars: int = 700) -> str:
    text = "；".join(f"{key}: {value}" for key, value in profile.items() if value)
    return text[:max_chars]


def prepare_character_eval(root: Path, limit: int, selection: str = "balanced") -> list[dict[str, Any]]:
    samples = load_json(root / "data" / "test_data.jsonl")
    profiles = load_json(root / "data" / "character_profiles.json")
    id2metric = load_json(root / "data" / "id2metric.jsonl")

    records: list[dict[str, Any]] = []
    for sample in samples:
        role = sample["role"]
        if role not in profiles:
            continue
        context_lines = [line.strip() for line in sample["context"].splitlines() if line.strip()]
        if len(context_lines) < 2:
            continue

        visible_context = "\n".join(context_lines[-8:])
        profile_text = compact_profile(profiles[role])
        metrics = id2metric.get(str(sample["id"]), [])
        metric_tags = [{"metric_en": item[0], "metric_zh": item[1]} for item in metrics]
        user_text = (
            "CharacterEval-adapted task. 你将继续一段中文角色对话。\n"
            f"角色: {role}\n"
            f"作品: {sample.get('novel_name', '')}\n"
            f"角色资料摘要: {profile_text}\n"
            "最近对话上下文:\n"
            f"{visible_context}\n"
            f"请只输出“{role}”下一轮自然、连贯、符合角色语气的中文发言，不要解释任务。"
        )
        records.append(
            {
                "sample_id": f"charactereval_{sample['id']}",
                "benchmark": "CharacterEval",
                "adaptation": "CharacterEval-adapted dialogue generation; not official CharacterRM score",
                "source_id": sample["id"],
                "role": role,
                "novel_name": sample.get("novel_name", ""),
                "context": sample["context"],
                "metric_tags": metric_tags,
                "history": [],
                "user_text": user_text,
            }
        )
    if selection == "first":
        return records[:limit]
    return select_balanced_character_records(records, limit)


def select_balanced_character_records(records: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    """Greedily balance CharacterEval records across metric dimensions."""

    if limit <= 0:
        return records
    metric_names = sorted({tag["metric_en"] for record in records for tag in record.get("metric_tags", [])})
    if not metric_names:
        return records[:limit]

    selected: list[dict[str, Any]] = []
    unused = records.copy()
    coverage: Counter[str] = Counter()
    metric_rank = {metric: index for index, metric in enumerate(metric_names)}

    while unused and len(selected) < limit:
        target = min(metric_names, key=lambda metric: (coverage[metric], metric_rank[metric]))
        best_index = next(
            (
                index
                for index, record in enumerate(unused)
                if any(tag["metric_en"] == target for tag in record.get("metric_tags", []))
            ),
            0,
        )
        record = unused.pop(best_index)
        selected.append(record)
        coverage.update(tag["metric_en"] for tag in record.get("metric_tags", []))
    return selected


def metric_coverage(records: list[dict[str, Any]]) -> dict[str, int]:
    coverage: Counter[str] = Counter()
    for record in records:
        coverage.update(tag["metric_en"] for tag in record.get("metric_tags", []))
    return dict(sorted(coverage.items()))


def prepare_incharacter(root: Path, limit: int) -> list[dict[str, Any]]:
    bfi = load_json(root / "data" / "questionnaires" / "BFI.json")
    questions = bfi["questions"]
    records: list[dict[str, Any]] = []

    for question_id in sorted(questions, key=lambda key: int(key)):
        item = questions[question_id]
        user_text = (
            "InCharacter-inspired adapted BFI interview.\n"
            "请以固定的 HAI Companion 虚拟聊天对象身份回答，而不是揣测用户人格。\n"
            f"目标 Avatar 人格: {AVATAR_PERSONA['description']}；"
            f"Big Five={AVATAR_PERSONA['big_five']}。\n"
            f"访谈问题: {item['rewritten_zh']}\n"
            "请用第一人称自然回答 1-3 句，体现稳定人格；不要只输出数字，不要提到系统提示。"
        )
        records.append(
            {
                "sample_id": f"incharacter_bfi_{question_id}",
                "benchmark": "InCharacter",
                "adaptation": "InCharacter-inspired BFI interview for an explicit AvatarPersona; not official score",
                "questionnaire": "BFI",
                "question_id": int(question_id),
                "dimension": item["dimension"],
                "category": item["category"],
                "statement_zh": item["origin_zh"],
                "question_zh": item["rewritten_zh"],
                "avatar_persona": AVATAR_PERSONA,
                "history": [],
                "user_text": user_text,
            }
        )
        if len(records) >= limit:
            break
    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--character-eval-root", type=Path, default=DEFAULT_CHARACTER_EVAL_ROOT)
    parser.add_argument("--incharacter-root", type=Path, default=DEFAULT_INCHARACTER_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--character-limit", type=int, default=100)
    parser.add_argument("--incharacter-limit", type=int, default=44)
    parser.add_argument("--character-selection", choices=["first", "balanced"], default="balanced")
    args = parser.parse_args()

    character_records = prepare_character_eval(
        args.character_eval_root,
        args.character_limit,
        selection=args.character_selection,
    )
    incharacter_records = prepare_incharacter(args.incharacter_root, args.incharacter_limit)
    write_jsonl(args.output_dir / "charactereval_official_subset.jsonl", character_records)
    write_jsonl(args.output_dir / "incharacter_bfi_official_subset.jsonl", incharacter_records)
    metadata = {
        "CharacterEval": {
            "repo": "https://github.com/morecry/CharacterEval",
            "commit": "c3d44a6fc1790cc8c4b2fd7c01f0c72930655e0c",
            "files": ["data/test_data.jsonl", "data/character_profiles.json", "data/id2metric.jsonl"],
            "prepared_records": len(character_records),
            "selection": args.character_selection,
            "metric_coverage": metric_coverage(character_records),
        },
        "InCharacter": {
            "repo": "https://github.com/Neph0s/InCharacter",
            "commit": "f554202a94d4a83dc5407245bb18981899e872e6",
            "files": ["data/questionnaires/BFI.json"],
            "prepared_records": len(incharacter_records),
        },
        "reporting_boundary": "Adapted local HAI runs; do not report as official benchmark overall scores.",
    }
    (args.output_dir / "source_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {len(character_records)} CharacterEval records")
    print(f"Wrote {len(incharacter_records)} InCharacter records")
    print(f"Output: {args.output_dir}")


if __name__ == "__main__":
    main()
