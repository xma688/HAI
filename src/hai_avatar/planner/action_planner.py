"""Rule-based validation layer for avatar commands."""

import time
from collections.abc import Iterable

from hai_avatar.planner.mapping import load_action_mapping
from hai_avatar.schemas import (
    AvatarCommand,
    EmotionType,
    ExpressionType,
    GestureType,
    LLMAvatarResponse,
    VoiceStyleType,
)


class ActionPlanner:
    """Normalize LLM labels and apply lightweight consistency rules."""

    def __init__(self, max_gestures: int = 2, enable_cooldown: bool = True) -> None:
        self.max_gestures = max_gestures
        self.enable_cooldown = enable_cooldown
        self.mapping = load_action_mapping()
        self._last_gesture_at: dict[tuple[str, GestureType], float] = {}

    def plan(
        self,
        llm_response: LLMAvatarResponse,
        user_text: str = "",
        context_id: str = "default",
    ) -> tuple[AvatarCommand, list[str]]:
        warnings: list[str] = []
        emotion = self._coerce_enum(EmotionType, llm_response.emotion, EmotionType.neutral, "emotion", warnings)
        expression = self._coerce_enum(
            ExpressionType, llm_response.expression, ExpressionType.neutral, "expression", warnings
        )
        voice_style = self._coerce_enum(
            VoiceStyleType, llm_response.voice_style, VoiceStyleType.neutral, "voice_style", warnings
        )
        gestures = self._normalize_gestures(llm_response.gestures, warnings)

        expression, gestures = self._apply_consistency_rules(emotion, expression, gestures, user_text, warnings)
        gestures = self._apply_cooldown(gestures, warnings, context_id)
        if not gestures:
            gestures = [GestureType.idle]
        command = AvatarCommand(
            emotion=emotion,
            expression=expression,
            gestures=gestures[: self.max_gestures],
            voice_style=voice_style,
            gesture_intensity=llm_response.gesture_intensity,
            speaking_rate=llm_response.speaking_rate,
            pause_before_speech_ms=llm_response.pause_before_speech_ms,
        )
        return command, warnings

    def _coerce_enum(self, enum_cls, value: str, default, field_name: str, warnings: list[str]):
        try:
            return enum_cls(value)
        except ValueError:
            warnings.append(f"Unknown {field_name} '{value}' downgraded to '{default.value}'.")
            return default

    def _normalize_gestures(self, raw_gestures: Iterable[str], warnings: list[str]) -> list[GestureType]:
        gestures: list[GestureType] = []
        for raw in raw_gestures or ["idle"]:
            try:
                gestures.append(GestureType(raw))
            except ValueError:
                warnings.append(f"Unknown gesture '{raw}' downgraded to 'idle'.")
                gestures.append(GestureType.idle)
        if len(gestures) > self.max_gestures:
            warnings.append(f"Gestures truncated to first {self.max_gestures}.")
            gestures = gestures[: self.max_gestures]
        return gestures

    def _apply_consistency_rules(
        self,
        emotion: EmotionType,
        expression: ExpressionType,
        gestures: list[GestureType],
        user_text: str,
        warnings: list[str],
    ) -> tuple[ExpressionType, list[GestureType]]:
        if emotion == EmotionType.supportive and expression == ExpressionType.surprised:
            warnings.append("supportive + surprised corrected to soft_smile.")
            expression = ExpressionType.soft_smile
        if emotion == EmotionType.serious and expression == ExpressionType.smile:
            warnings.append("serious + smile corrected to serious.")
            expression = ExpressionType.serious
        if emotion == EmotionType.apologetic and GestureType.small_bow not in gestures:
            warnings.append("apologetic response prefers small_bow.")
            gestures = [GestureType.small_bow, *gestures]
        if emotion == EmotionType.confused and gestures == [GestureType.idle]:
            gestures = [GestureType.head_tilt]
        if emotion == EmotionType.thoughtful and gestures == [GestureType.idle]:
            gestures = [GestureType.think]
        if emotion == EmotionType.happy and expression == ExpressionType.neutral:
            expression = ExpressionType.smile

        lowered = user_text.lower()
        if any(keyword in lowered for keyword in ["再见", "拜拜", "下次见", "回头见"]):
            gestures = self._prepend_unique(GestureType.wave, gestures)
        if any(keyword in lowered for keyword in ["解释", "说明", "概念", "为什么", "怎么"]):
            gestures = self._prepend_unique(GestureType.explain, gestures)

        return expression, gestures[: self.max_gestures]

    def _apply_cooldown(
        self,
        gestures: list[GestureType],
        warnings: list[str],
        context_id: str,
    ) -> list[GestureType]:
        if not self.enable_cooldown:
            return gestures
        now = time.monotonic()
        cooldowns = self.mapping.get("cooldowns_seconds", {})
        planned: list[GestureType] = []
        for gesture in gestures:
            seconds = float(cooldowns.get(gesture.value, 0))
            cooldown_key = (context_id, gesture)
            last_seen = self._last_gesture_at.get(cooldown_key)
            if seconds and last_seen is not None and now - last_seen < seconds:
                replacement = GestureType.nod if gesture != GestureType.nod else GestureType.idle
                warnings.append(f"Gesture '{gesture.value}' is cooling down; replaced by '{replacement.value}'.")
                planned.append(replacement)
                continue
            planned.append(gesture)
            if gesture != GestureType.idle:
                self._last_gesture_at[cooldown_key] = now
        return planned

    def clear_context(self, context_id: str) -> None:
        self._last_gesture_at = {
            key: value for key, value in self._last_gesture_at.items() if key[0] != context_id
        }

    def _prepend_unique(self, gesture: GestureType, gestures: list[GestureType]) -> list[GestureType]:
        return [gesture, *[item for item in gestures if item != gesture]]
