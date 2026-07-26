"""Adjust AvatarCommand parameters based on user profile constraints."""

import logging

from hai_avatar.schemas import AvatarCommand, GestureType, UserProfile

logger = logging.getLogger(__name__)

_GESTURE_FREQUENCY_CAPS = {"minimal": 1, "moderate": 2, "frequent": 3}
_PACE_RATE_MAP = {"slow": 0.8, "moderate": 1.0, "fast": 1.25}


class PostProcessor:
    def __init__(self, max_gestures_fallback: int = 2) -> None:
        self._max_gestures_fallback = max_gestures_fallback

    def apply(self, command: AvatarCommand, profile: UserProfile) -> AvatarCommand:
        prefs = profile.preferences

        intensity = round(command.gesture_intensity * prefs.expressiveness_tolerance, 3)
        intensity = max(0.0, min(1.0, intensity))

        max_count = _GESTURE_FREQUENCY_CAPS.get(prefs.gesture_frequency, self._max_gestures_fallback)
        gestures = self._filter_by_affinity(command.gestures, profile.gesture_affinity)[:max_count]
        if not gestures:
            gestures = [GestureType.idle]

        rate = round(command.speaking_rate * _PACE_RATE_MAP.get(prefs.pace, 1.0), 3)
        rate = max(0.5, min(2.0, rate))

        adjusted = command.model_copy(
            update={
                "gesture_intensity": intensity,
                "gestures": gestures,
                "speaking_rate": rate,
            }
        )
        if adjusted != command:
            logger.info(
                "PostProcessor adjusted command: intensity %.2f->%.2f speaking_rate %.2f->%.2f gestures %s->%s",
                command.gesture_intensity, adjusted.gesture_intensity,
                command.speaking_rate, adjusted.speaking_rate,
                [g.value for g in command.gestures],
                [g.value for g in adjusted.gestures],
            )
        return adjusted

    @staticmethod
    def _filter_by_affinity(
        gestures: list[GestureType],
        affinity: dict[str, float],
    ) -> list[GestureType]:
        if not affinity:
            return gestures
        result: list[GestureType] = []
        for g in gestures:
            score = affinity.get(g.value, 0.5)
            if score < 0.2 and g != GestureType.idle:
                replacement = GestureType.nod if g != GestureType.nod else GestureType.idle
                result.append(replacement)
                logger.debug("Gesture '%s' filtered (affinity %.2f) -> '%s'", g.value, score, replacement.value)
            else:
                result.append(g)
        return result
