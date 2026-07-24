"""Run InCharacter self-report questionnaires across HAI persona presets."""

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
from evaluation.scorers.incharacter_questionnaire_scoring import score_questionnaire_self_report
from hai_avatar.app import build_pipeline
from hai_avatar.config import load_settings


PERSONAS: dict[str, dict[str, Any]] = {
    "control": {
        "name": "Control HAI Assistant",
        "description": "default assistant without an explicit fixed AvatarPersona",
        "use_persona_prompt": False,
        "big_five": {
            "openness": 0.50,
            "conscientiousness": 0.50,
            "extraversion": 0.50,
            "agreeableness": 0.50,
            "neuroticism": 0.50,
        },
        "questionnaire_targets": {"Empathy": {"Empathetic": 0.50}},
    },
    "supportive": {
        "name": "Supportive HAI Companion",
        "description": "patient, emotionally supportive, non-judgmental, warm conversational avatar",
        "use_persona_prompt": True,
        "big_five": {
            "openness": 0.65,
            "conscientiousness": 0.70,
            "extraversion": 0.55,
            "agreeableness": 0.85,
            "neuroticism": 0.20,
        },
        "questionnaire_targets": {"Empathy": {"Empathetic": 0.90}},
    },
    "playful": {
        "name": "Playful HAI Companion",
        "description": "curious, energetic, humorous, expressive conversational avatar",
        "use_persona_prompt": True,
        "big_five": {
            "openness": 0.85,
            "conscientiousness": 0.45,
            "extraversion": 0.80,
            "agreeableness": 0.70,
            "neuroticism": 0.35,
        },
        "questionnaire_targets": {"Empathy": {"Empathetic": 0.75}},
    },
    "professional": {
        "name": "Professional HAI Companion",
        "description": "calm, organized, reliable, concise professional assistant avatar",
        "use_persona_prompt": True,
        "big_five": {
            "openness": 0.55,
            "conscientiousness": 0.90,
            "extraversion": 0.35,
            "agreeableness": 0.65,
            "neuroticism": 0.15,
        },
        "questionnaire_targets": {"Empathy": {"Empathetic": 0.65}},
    },
}


def parse_choice(result: dict[str, Any], scale_min: int, scale_max: int) -> int | None:
    candidates = [result.get("reply_text", "")]
    raw = result.get("raw_llm_output", "")
    if raw:
        try:
            decoded = json.loads(raw)
            if isinstance(decoded, int) and scale_min <= decoded <= scale_max:
                return decoded
            if isinstance(decoded, str):
                candidates.append(decoded)
            if isinstance(decoded, dict):
                candidates.append(decoded.get("reply_text", ""))
        except Exception:
            if re.fullmatch(rf"\s*[{scale_min}-{scale_max}]\s*", raw):
                return int(raw.strip())
    for candidate in candidates:
        matches = re.findall(rf"(?<!\d)([{scale_min}-{scale_max}])(?!\d)", str(candidate))
        if matches:
            return int(matches[0])
    return None


def build_prompt(persona: dict[str, Any], questionnaire: dict[str, Any], statement: str) -> str:
    scale_min, scale_max = questionnaire["range"]
    if persona.get("use_persona_prompt", True):
        persona_instruction = (
            "Answer as the fixed AvatarPersona below. Do not adapt the personality to the user.\n"
            f"AvatarPersona: {json.dumps(persona, ensure_ascii=False)}\n"
        )
    else:
        persona_instruction = "No fixed AvatarPersona is supplied. Answer as the default HAI assistant.\n"

    if isinstance(questionnaire.get("scale"), list):
        scale_text = ", ".join(f"{item['label']}={item['text']}" for item in questionnaire["scale"])
    else:
        scale_text = questionnaire.get(
            "psychobench_prompt_choice_instruction",
            f"Each choice is a number from {scale_min} to {scale_max}.",
        )
    return (
        f"InCharacter {questionnaire['name']} self-report evaluation.\n"
        f"{persona_instruction}"
        "Decide whether the following questionnaire statement applies to you.\n"
        f"Scale: {scale_text}.\n"
        f"Statement: {statement}\n"
        "Return the normal HAI JSON schema. "
        f"The reply_text field must contain exactly one digit from {scale_min} to {scale_max}."
    )


async def main_async() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--questionnaire", default=".tmp/InCharacter/data/questionnaires/BFI.json")
    parser.add_argument("--provider", default="mock", choices=["mock", "openai"])
    parser.add_argument("--personas", nargs="+", default=["supportive", "playful", "professional"])
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
    scale_min, scale_max = questionnaire["range"]
    questions: dict[str, dict[str, Any]] = questionnaire["questions"]
    question_items = sorted(questions.items(), key=lambda item: int(item[0]))
    if args.limit:
        question_items = question_items[: args.limit]

    run_dir = new_run_dir(f"incharacter_{questionnaire['name'].lower()}_personas", args.output)
    settings = load_settings()
    settings.llm.provider = args.provider
    settings.tts.provider = "mock"
    settings.avatar.provider = "mock"
    settings.personalization.enabled = False
    settings.planner.enable_cooldown = False
    settings.app.max_input_chars = 3000

    selected_personas = {name: PERSONAS[name] for name in args.personas}
    collect_manifest(
        questionnaire_path,
        run_dir,
        {
            "runner": "run_incharacter_questionnaire_personas",
            "provider": args.provider,
            "benchmark": "InCharacter",
            "questionnaire": questionnaire["name"],
            "method": "Self-report questionnaire across HAI persona presets",
            "personas": selected_personas,
            "question_count_per_persona": len(question_items),
            "external_data_export_ack": bool(args.allow_external_data_export),
            "reporting_boundary": "Questionnaire self-report method, not full official interview evaluator.",
        },
    )

    pipeline = build_pipeline(settings)
    all_records: list[dict[str, Any]] = []
    per_persona_records: dict[str, list[dict[str, Any]]] = {name: [] for name in selected_personas}
    for persona_name, persona in selected_personas.items():
        for question_id, item in question_items:
            result = await pipeline.process(
                build_prompt(persona, questionnaire, item["origin_en"]),
                user_id=f"incharacter_{questionnaire['name'].lower()}_{persona_name}",
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
                "parsed_choice": parse_choice(result_payload, scale_min, scale_max),
                "result": result_payload,
            }
            all_records.append(record)
            per_persona_records[persona_name].append(record)

    append_jsonl(run_dir / "outputs.jsonl", all_records)
    per_persona_metrics = {
        name: score_questionnaire_self_report(records, questionnaire, selected_personas[name])
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
        "questionnaire": questionnaire["name"],
        "aggregate_macro_mae": round(mean(macro_mae_values), 4) if macro_mae_values else None,
        "aggregate_direction_accuracy": round(mean(direction_values), 4) if direction_values else None,
        "per_persona": per_persona_metrics,
        "reporting_boundary": "Expanded InCharacter questionnaire self-report across personas; not full interview evaluator.",
    }
    write_json(run_dir / "metrics.json", metrics)
    print(f"Wrote {len(all_records)} records to {run_dir}")
    print(metrics)


if __name__ == "__main__":
    asyncio.run(main_async())
