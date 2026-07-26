"""Parsing and normalization helpers for LLM avatar output."""

import json
import re
from typing import Any

from pydantic import ValidationError

from hai_avatar.exceptions import LLMResponseParseError
from hai_avatar.schemas import LLMAvatarResponse


def parse_llm_avatar_response(raw_text: str) -> LLMAvatarResponse:
    """Parse JSON, Markdown-wrapped JSON, or plain text into LLMAvatarResponse."""

    errors: list[str] = []
    for candidate in (raw_text, _extract_json_object(raw_text)):
        if not candidate:
            continue
        data: Any = None
        try:
            data = json.loads(candidate)
            if not isinstance(data, dict):
                return _plain_text_response(str(data))
            return LLMAvatarResponse.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as exc:
            errors.append(str(exc))
            if isinstance(data, dict):
                reply_text = data.get("reply_text")
                if isinstance(reply_text, str) and reply_text.strip():
                    return _plain_text_response(reply_text.strip())
    if raw_text.strip():
        return _plain_text_response(raw_text.strip())
    raise LLMResponseParseError("; ".join(errors) or "No JSON object found in LLM response.")


def _plain_text_response(reply_text: str) -> LLMAvatarResponse:
    return LLMAvatarResponse(
        reply_text=reply_text,
        emotion="neutral",
        expression="neutral",
        gestures=["idle"],
        voice_style="neutral",
        gesture_intensity=0.3,
        speaking_rate=1.0,
        pause_before_speech_ms=0,
    )


def fallback_llm_response(user_text: str) -> LLMAvatarResponse:
    """Return a safe neutral response when parsing or generation fails."""

    _ = user_text
    return LLMAvatarResponse(
        reply_text="抱歉，我刚才没有稳定生成回复。我们可以先继续当前话题。",
        emotion="neutral",
        expression="neutral",
        gestures=["idle"],
        voice_style="neutral",
        gesture_intensity=0.3,
        speaking_rate=1.0,
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
