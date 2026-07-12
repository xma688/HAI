"""Parsing and normalization helpers for LLM avatar output."""

import json
import re
from typing import Any

from pydantic import ValidationError

from hai_avatar.exceptions import LLMResponseParseError
from hai_avatar.schemas import LLMAvatarResponse


def parse_llm_avatar_response(raw_text: str) -> LLMAvatarResponse:
    """Parse JSON, including Markdown-wrapped JSON, into LLMAvatarResponse."""

    errors: list[str] = []
    for candidate in (raw_text, _extract_json_object(raw_text)):
        if not candidate:
            continue
        try:
            data: dict[str, Any] = json.loads(candidate)
            return LLMAvatarResponse.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as exc:
            errors.append(str(exc))
    raise LLMResponseParseError("; ".join(errors) or "No JSON object found in LLM response.")


def fallback_llm_response(user_text: str) -> LLMAvatarResponse:
    """Return a safe neutral response when parsing or generation fails."""

    _ = user_text
    return LLMAvatarResponse(
        reply_text="抱歉，我刚才没有稳定生成回复。我们可以先继续当前话题。",
        emotion="neutral",
        expression="neutral",
        gestures=["idle"],
        voice_style="neutral",
        pause_before_speech_ms=0,
    )


def _extract_json_object(raw_text: str) -> str | None:
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced.group(1)
    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start >= 0 and end > start:
        return raw_text[start : end + 1]
    return None
