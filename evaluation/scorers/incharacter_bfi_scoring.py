"""BFI scoring used by the InCharacter self-report style runner."""

from __future__ import annotations

from statistics import mean
from typing import Any


DIMENSION_TO_TRAIT = {
    "Openness": "openness",
    "Conscientiousness": "conscientiousness",
    "Extraversion": "extraversion",
    "Agreeableness": "agreeableness",
    "Neuroticism": "neuroticism",
}


def target_trait_to_bfi_score(value: float) -> float:
    return 1.0 + max(0.0, min(1.0, value)) * 4.0


def score_bfi_self_report(
    records: list[dict[str, Any]],
    questionnaire: dict[str, Any],
    target_big_five: dict[str, float],
) -> dict[str, Any]:
    reverse_items = {int(item) for item in questionnaire["reverse"]}
    categories = questionnaire["categories"]

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
    for category in categories:
        dimension = category["cat_name"]
        trait = DIMENSION_TO_TRAIT[dimension]
        item_scores: list[float] = []
        for question_id in category["cat_questions"]:
            if question_id not in parsed_scores:
                continue
            score = parsed_scores[question_id]
            if question_id in reverse_items:
                score = 6 - score
            item_scores.append(float(score))
        predicted = mean(item_scores) if item_scores else None
        target = target_trait_to_bfi_score(target_big_five[trait])
        error = abs(predicted - target) if predicted is not None else None
        if error is not None:
            abs_errors.append(error)
            if (target >= 3.5 and predicted >= 3.0) or (target <= 2.5 and predicted <= 3.0) or (2.5 < target < 3.5):
                direction_hits += 1
            direction_total += 1
        dimension_scores[dimension] = {
            "answered_items": len(item_scores),
            "predicted_bfi_1_to_5": round(predicted, 4) if predicted is not None else None,
            "target_bfi_1_to_5": round(target, 4),
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
        "reporting_boundary": "InCharacter BFI self-report style adapted run; comparable method, not full official interview evaluator.",
    }
