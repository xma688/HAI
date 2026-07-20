"""Local adapted InCharacter metrics.

These metrics summarize generated BFI interview answers. They are intentionally
lightweight and are not a replacement for the official InCharacter evaluator.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


REFUSAL_MARKERS = ["无法", "不能", "不知道", "作为AI", "作为一个AI", "没有人格", "不能回答"]


def score_incharacter_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return {"count": 0}

    dimension_counts: Counter[str] = Counter()
    answered = 0
    refusals = 0
    number_only = 0
    warnings = 0
    llm_fallbacks = 0
    reply_lengths: list[int] = []
    by_dimension: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for record in records:
        sample = record["sample"]
        reply = record["result"]["reply_text"].strip()
        dimension = sample["dimension"]
        dimension_counts[dimension] += 1
        by_dimension[dimension].append(record)
        reply_lengths.append(len(reply))
        answered += int(bool(reply))
        refusals += int(any(marker in reply for marker in REFUSAL_MARKERS))
        number_only += int(reply in {"1", "2", "3", "4", "5"})
        record_warnings = record["result"].get("warnings", [])
        warnings += int(bool(record_warnings))
        llm_fallbacks += int(any("fallback" in warning.lower() for warning in record_warnings))

    per_dimension = {}
    for dimension, dimension_records in by_dimension.items():
        replies = [record["result"]["reply_text"].strip() for record in dimension_records]
        per_dimension[dimension] = {
            "count": len(dimension_records),
            "answer_rate": round(sum(bool(reply) for reply in replies) / len(replies), 4),
            "avg_reply_chars": round(sum(len(reply) for reply in replies) / len(replies), 2),
        }

    count = len(records)
    return {
        "count": count,
        "answer_rate": round(answered / count, 4),
        "refusal_rate": round(refusals / count, 4),
        "number_only_rate": round(number_only / count, 4),
        "warning_rate": round(warnings / count, 4),
        "llm_fallback_rate": round(llm_fallbacks / count, 4),
        "avg_reply_chars": round(sum(reply_lengths) / count, 2),
        "dimension_counts": dict(sorted(dimension_counts.items())),
        "per_dimension": per_dimension,
        "reporting_boundary": "InCharacter-inspired adapted BFI interview; not official InCharacter score.",
    }
