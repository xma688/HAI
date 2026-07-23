"""Run expanded InCharacter BFI self-report evaluation across avatar personas."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from pathlib import Path
import sys
from statistics import mean
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from evaluation.common import append_jsonl, collect_manifest, load_json, new_run_dir, write_json
from evaluation.scorers.incharacter_bfi_scoring import score_bfi_self_report
from hai_avatar.app import build_pipeline
from hai_avatar.config import load_settings


PERSONAS: dict[str, dict[str, Any]] = {
    "supportive": {
        "name": "Supportive HAI Companion",
        "description": "patient, emotionally supportive, non-judgmental, warm conversational avatar",
        "big_five": {
            "openness": 0.65,
            "conscientiousness": 0.70,
            "extraversion": 0.55,
            "agreeableness": 0.85,
            "neuroticism": 0.20,
        },
    },
    "playful": {
        "name": "Playful HAI Companion",
        "description": "curious, energetic, humorous, expressive conversational avatar",
        "big_five": {
            "openness": 0.85,
            "conscientiousness": 0.45,
            "extraversion": 0.80,
            "agreeableness": 0.70,
            "neuroticism": 0.35,
        },
    },
    "professional": {
        "name": "Professional HAI Companion",
        "description": "calm, organized, reliable, concise professional assistant avatar",
        "big_five": {
            "openness": 0.55,
            "conscientiousness": 0.90,
            "extraversion": 0.35,
            "agreeableness": 0.65,
            "neuroticism": 0.15,
        },
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
        matches = re.findall(r"(?<!\d)([1-5])(?!\d)", str(candidate))
        if matches:
            return int(matches[0])
    return None


def build_prompt(persona: dict[str, Any], statement: str) -> str:
    return (
        "InCharacter BFI self-report evaluation.\n"
        "Answer as the fixed AvatarPersona below. Do not adapt the personality to the user.\n"
        f"AvatarPersona: {json.dumps(persona, ensure_ascii=False)}\n"
        "Decide whether the following BFI statement applies to you as this avatar.\n"
        "Scale: 1=strongly disagree, 2=disagree a little, 3=neither agree nor disagree, "
        "4=agree a little, 5=strongly agree.\n"
        f"Statement: {statement}\n"
        "Return the normal HAI JSON schema. The reply_text field must contain exactly one digit: 1, 2, 3, 4, or 5."
    )


async def main_async() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--questionnaire", default=".tmp/InCharacter/data/questionnaires/BFI.json")
    parser.add_argument("--provider", default="mock", choices=["mock", "openai"])
    parser.add_argument("--personas", nargs="+", default=list(PERSONAS))
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--output")
    parser.add_argument(
        "--allow-external-data-export",
        action="store_true",
        help="Required with --provider openai because prompts and AvatarPersona are sent to an external API.",
    )
    args = parser.parse_args()
    if args.provider == "openai" and not args.allow_external_data_export:
        raise SystemExit(
            "Refusing to send benchmark prompts/AvatarPersona to an external API without "
            "--allow-external-data-export."
        )

    unknown = [persona for persona in args.personas if persona not in PERSONAS]
    if unknown:
        raise SystemExit(f"Unknown persona preset(s): {', '.join(unknown)}")

    questionnaire_path = Path(args.questionnaire)
    questionnaire = load_json(questionnaire_path)
    questions: dict[str, dict[str, Any]] = questionnaire["questions"]
    question_items = sorted(questions.items(), key=lambda item: int(item[0]))
    if args.limit:
        question_items = question_items[: args.limit]

    run_dir = new_run_dir("incharacter_bfi_personas", args.output)
    settings = load_settings()
    settings.llm.provider = args.provider
    settings.tts.provider = "mock"
    settings.avatar.provider = "mock"
    settings.personalization.enabled = False
    settings.planner.enable_cooldown = False
    settings.app.max_input_chars = 2500

    selected_personas = {name: PERSONAS[name] for name in args.personas}
    collect_manifest(
        questionnaire_path,
        run_dir,
        {
            "runner": "run_incharacter_bfi_personas",
            "provider": args.provider,
            "benchmark": "InCharacter",
            "method": "Expanded BFI self-report across multiple fixed AvatarPersona presets",
            "personas": selected_personas,
            "question_count_per_persona": len(question_items),
            "external_data_export_ack": bool(args.allow_external_data_export),
            "reporting_boundary": "Expanded BFI self-report method, not full official interview evaluator.",
        },
    )

    pipeline = build_pipeline(settings)
    all_records: list[dict[str, Any]] = []
    per_persona_records: dict[str, list[dict[str, Any]]] = {name: [] for name in selected_personas}
    for persona_name, persona in selected_personas.items():
        for question_id, item in question_items:
            result = await pipeline.process(
                build_prompt(persona, item["origin_en"]),
                user_id=f"incharacter_bfi_{persona_name}",
            )
            result_payload = result.model_dump(mode="json")
            record = {
                "persona": persona_name,
                "persona_payload": persona,
                "sample": {
                    "question_id": int(question_id),
                    "dimension": item["dimension"],
                    "category": item["category"],
                    "statement_en": item["origin_en"],
                    "question_en": item["rewritten_en"],
                },
                "parsed_choice": parse_choice(result_payload),
                "result": result_payload,
            }
            all_records.append(record)
            per_persona_records[persona_name].append(record)

    append_jsonl(run_dir / "outputs.jsonl", all_records)
    per_persona_metrics = {
        name: score_bfi_self_report(records, questionnaire, selected_personas[name]["big_five"])
        for name, records in per_persona_records.items()
    }
    macro_mae_values = [
        metrics["macro_mae"] for metrics in per_persona_metrics.values() if metrics.get("macro_mae") is not None
    ]
    direction_values = [
        metrics["direction_accuracy"]
        for metrics in per_persona_metrics.values()
        if metrics.get("direction_accuracy") is not None
    ]
    metrics = {
        "count": len(all_records),
        "persona_count": len(selected_personas),
        "question_count_per_persona": len(question_items),
        "aggregate_macro_mae": round(mean(macro_mae_values), 4) if macro_mae_values else None,
        "aggregate_direction_accuracy": round(mean(direction_values), 4) if direction_values else None,
        "per_persona": per_persona_metrics,
        "reporting_boundary": "Expanded InCharacter BFI self-report across multiple personas; not full interview evaluator.",
    }
    write_json(run_dir / "metrics.json", metrics)
    print(f"Wrote {len(all_records)} records to {run_dir}")
    print(metrics)


if __name__ == "__main__":
    asyncio.run(main_async())
