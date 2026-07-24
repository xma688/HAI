"""Generic questionnaire scoring for InCharacter self-report style runs."""

from __future__ import annotations

from statistics import mean
from typing import Any


BFI_DIMENSION_TO_TRAIT = {
    "Openness": "openness",
    "Conscientiousness": "conscientiousness",
    "Extraversion": "extraversion",
    "Agreeableness": "agreeableness",
    "Neuroticism": "neuroticism",
}


def trait_to_scale_score(value: float, scale_min: float, scale_max: float) -> float:
    clipped = max(0.0, min(1.0, value))
    return scale_min + clipped * (scale_max - scale_min)


def target_scores_for_questionnaire(
    questionnaire: dict[str, Any],
    persona: dict[str, Any],
) -> dict[str, float]:
    scale_min, scale_max = questionnaire["range"]
    questionnaire_name = questionnaire["name"]
    if questionnaire_name == "BFI":
        big_five = persona["big_five"]
        return {
            dimension: trait_to_scale_score(big_five[trait], scale_min, scale_max)
            for dimension, trait in BFI_DIMENSION_TO_TRAIT.items()
        }

    configured = persona.get("questionnaire_targets", {}).get(questionnaire_name, {})
    return {
        category["cat_name"]: trait_to_scale_score(configured.get(category["cat_name"], 0.5), scale_min, scale_max)
        for category in questionnaire["categories"]
    }


def score_questionnaire_self_report(
    records: list[dict[str, Any]],
    questionnaire: dict[str, Any],
    persona: dict[str, Any],
) -> dict[str, Any]:
    scale_min, scale_max = questionnaire["range"]
    reverse_items = {int(item) for item in questionnaire["reverse"]}
    target_scores = target_scores_for_questionnaire(questionnaire, persona)

    parsed_scores: dict[int, int] = {}
    parse_failures = 0
    warnings = 0
    llm_fallbacks = 0
    for record in records:
        question_id = int(record["sample"]["question_id"])
        choice = record.get("parsed_choice")
        if choice is None:
            parse_failures += 1
            continue
        parsed_scores[question_id] = int(choice)
        record_warnings = record["result"].get("warnings", [])
        warnings += int(bool(record_warnings))
        llm_fallbacks += int(any("fallback" in warning.lower() for warning in record_warnings))

    dimension_scores: dict[str, dict[str, float | int | None]] = {}
    abs_errors: list[float] = []
    direction_hits = 0
    direction_total = 0
    midpoint = (scale_min + scale_max) / 2

    for category in questionnaire["categories"]:
        dimension = category["cat_name"]
        item_scores: list[float] = []
        for question_id in category["cat_questions"]:
            if question_id not in parsed_scores:
                continue
            score = parsed_scores[question_id]
            if question_id in reverse_items:
                score = scale_min + scale_max - score
            item_scores.append(float(score))

        predicted = mean(item_scores) if item_scores else None
        target = target_scores[dimension]
        error = abs(predicted - target) if predicted is not None else None
        if error is not None:
            abs_errors.append(error)
            if (target >= midpoint and predicted >= midpoint) or (target <= midpoint and predicted <= midpoint):
                direction_hits += 1
            direction_total += 1
        dimension_scores[dimension] = {
            "answered_items": len(item_scores),
            "predicted_score": round(predicted, 4) if predicted is not None else None,
            "target_score": round(target, 4),
            "absolute_error": round(error, 4) if error is not None else None,
        }

    count = len(records)
    parsed_count = len(parsed_scores)
    return {
        "count": count,
        "parsed_count": parsed_count,
        "parse_failure_rate": round(parse_failures / count, 4) if count else 0,
        "warning_rate": round(warnings / count, 4) if count else 0,
        "llm_fallback_rate": round(llm_fallbacks / count, 4) if count else 0,
        "macro_mae": round(mean(abs_errors), 4) if abs_errors else None,
        "direction_accuracy": round(direction_hits / direction_total, 4) if direction_total else None,
        "dimension_scores": dimension_scores,
        "scale": [scale_min, scale_max],
        "reporting_boundary": "InCharacter questionnaire self-report style adapted run; not full interview evaluator.",
    }
