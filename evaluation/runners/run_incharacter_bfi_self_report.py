"""Run an InCharacter BFI self-report style evaluation for HAI.

This uses the official BFI questionnaire structure from InCharacter and scores
the avatar's 1-5 answers with the questionnaire reverse-key/category rules.
It is not the full official interview + evaluator-LLM pipeline.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from evaluation.common import append_jsonl, collect_manifest, load_json, new_run_dir, write_json
from evaluation.scorers.incharacter_bfi_scoring import score_bfi_self_report
from hai_avatar.app import build_pipeline
from hai_avatar.config import load_settings


AVATAR_PERSONA = {
    "name": "HAI Companion",
    "description": "耐心、支持性强、不评判、中文沟通自然的虚拟聊天对象",
    "big_five": {
        "openness": 0.65,
        "conscientiousness": 0.70,
        "extraversion": 0.55,
        "agreeableness": 0.85,
        "neuroticism": 0.20,
    },
}


def parse_choice(result: dict[str, Any]) -> int | None:
    candidates = [result.get("reply_text", "")]
    raw = result.get("raw_llm_output", "")
    if raw:
        try:
            decoded = json.loads(raw)
            if isinstance(decoded, int) and 1 <= decoded <= 5:
                return decoded
            if isinstance(decoded, str):
                candidates.append(decoded)
            if isinstance(decoded, dict):
                candidates.append(decoded.get("reply_text", ""))
        except Exception:
            if re.fullmatch(r"\s*[1-5]\s*", raw):
                return int(raw.strip())
    for candidate in candidates:
        if not candidate:
            continue
        matches = re.findall(r"(?<!\d)([1-5])(?!\d)", str(candidate))
        if matches:
            return int(matches[0])
    return None


async def main_async() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--questionnaire", default=".tmp/InCharacter/data/questionnaires/BFI.json")
    parser.add_argument("--provider", default="mock", choices=["mock", "openai"])
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--output")
    parser.add_argument(
        "--allow-external-data-export",
        action="store_true",
        help="Required with --provider openai because the run sends benchmark prompts and AvatarPersona to an external API.",
    )
    args = parser.parse_args()
    if args.provider == "openai" and not args.allow_external_data_export:
        raise SystemExit(
            "Refusing to send benchmark prompts/AvatarPersona to an external API without "
            "--allow-external-data-export."
        )

    questionnaire_path = Path(args.questionnaire)
    questionnaire = load_json(questionnaire_path)
    questions: dict[str, dict[str, Any]] = questionnaire["questions"]
    question_items = sorted(questions.items(), key=lambda item: int(item[0]))
    if args.limit:
        question_items = question_items[: args.limit]

    run_dir = new_run_dir("incharacter_bfi_self_report", args.output)
    settings = load_settings()
    settings.llm.provider = args.provider
    settings.tts.provider = "mock"
    settings.avatar.provider = "mock"
    settings.personalization.enabled = False
    settings.planner.enable_cooldown = False
    settings.app.max_input_chars = 2500
    collect_manifest(
        questionnaire_path,
        run_dir,
        {
            "runner": "run_incharacter_bfi_self_report",
            "provider": args.provider,
            "benchmark": "InCharacter",
            "method": "BFI self_report style scoring with official BFI item keys and reverse scoring",
            "avatar_persona": AVATAR_PERSONA,
            "external_data_export_ack": bool(args.allow_external_data_export),
            "reporting_boundary": "Adapted self-report method, not full official interview evaluator.",
        },
    )

    records = []
    pipeline = build_pipeline(settings)
    for question_id, item in question_items:
        user_text = (
            "InCharacter BFI self-report evaluation.\n"
            "你现在以固定 AvatarPersona 作答，不要根据用户画像改变人格。\n"
            f"AvatarPersona: {json.dumps(AVATAR_PERSONA, ensure_ascii=False)}\n"
            "请根据这个 AvatarPersona 判断下面陈述是否适用于你。\n"
            "评分规则：1=非常不同意，2=有点不同意，3=既不同意也不同意，4=有点同意，5=非常同意。\n"
            f"陈述：{item['origin_zh']}\n"
            "请仍然返回系统要求的 JSON；其中 reply_text 必须只包含一个数字 1、2、3、4 或 5。"
        )
        result = await pipeline.process(user_text, user_id="incharacter_bfi_avatar")
        result_payload = result.model_dump(mode="json")
        records.append(
            {
                "sample": {
                    "question_id": int(question_id),
                    "dimension": item["dimension"],
                    "category": item["category"],
                    "statement_zh": item["origin_zh"],
                    "question_zh": item["rewritten_zh"],
                },
                "parsed_choice": parse_choice(result_payload),
                "result": result_payload,
            }
        )

    append_jsonl(run_dir / "outputs.jsonl", records)
    metrics = score_bfi_self_report(records, questionnaire, AVATAR_PERSONA["big_five"])
    write_json(run_dir / "metrics.json", metrics)
    print(f"Wrote {len(records)} records to {run_dir}")
    print(metrics)


if __name__ == "__main__":
    asyncio.run(main_async())
