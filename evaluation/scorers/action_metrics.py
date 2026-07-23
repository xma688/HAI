"""Lightweight action/voice scoring for local gold samples."""

from __future__ import annotations

from typing import Any


def score_action_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return {"count": 0}
    totals = {
        "emotion_hit": 0,
        "expression_hit": 0,
        "gesture_hit": 0,
        "voice_hit": 0,
        "intensity_hit": 0,
        "speaking_rate_hit": 0,
        "forbidden_violations": 0,
    }
    for record in records:
        gold = record["gold"]["acceptable"]
        forbidden = record["gold"].get("forbidden", {})
        cmd = record["result"]["avatar_command"]
        gestures = set(cmd["gestures"])
        totals["emotion_hit"] += int(cmd["emotion"] in gold.get("emotion", []))
        totals["expression_hit"] += int(cmd["expression"] in gold.get("expression", []))
        totals["gesture_hit"] += int(bool(gestures.intersection(gold.get("gestures", []))))
        totals["voice_hit"] += int(cmd["voice_style"] in gold.get("voice_style", []))
        lo, hi = gold.get("gesture_intensity", [0.0, 1.0])
        totals["intensity_hit"] += int(lo <= cmd["gesture_intensity"] <= hi)
        lo, hi = gold.get("speaking_rate", [0.9, 1.1])
        totals["speaking_rate_hit"] += int(lo <= cmd["speaking_rate"] <= hi)
        if set(forbidden.get("gestures", [])).intersection(gestures):
            totals["forbidden_violations"] += 1
        if cmd["expression"] in forbidden.get("expression", []):
            totals["forbidden_violations"] += 1
    count = len(records)
    return {
        "count": count,
        **{f"{key}_rate": round(value / count, 4) for key, value in totals.items() if key != "forbidden_violations"},
        "forbidden_violations": totals["forbidden_violations"],
    }
