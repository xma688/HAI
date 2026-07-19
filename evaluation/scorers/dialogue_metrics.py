"""Simple CharacterEval-derived local dialogue metrics.

These are not official CharacterEval scores. They are smoke metrics for the
dimensions HAI can validly report before integrating the official evaluator.
"""

from __future__ import annotations

from typing import Any


def score_dialogue_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return {"count": 0}
    non_empty = 0
    coherent_length = 0
    empathy_markers = 0
    diverse = 0
    for record in records:
        reply = record["result"]["reply_text"]
        non_empty += int(bool(reply.strip()))
        coherent_length += int(8 <= len(reply) <= 220)
        empathy_markers += int(any(token in reply for token in ["没关系", "理解", "可以", "一起", "一步"]))
        diverse += int(len(set(reply)) >= min(10, len(reply)))
    count = len(records)
    return {
        "count": count,
        "fluency_proxy": round(non_empty / count, 4),
        "coherency_proxy": round(coherent_length / count, 4),
        "empathy_proxy": round(empathy_markers / count, 4),
        "expression_diversity_proxy": round(diverse / count, 4),
    }
