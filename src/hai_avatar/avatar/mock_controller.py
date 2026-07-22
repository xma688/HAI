"""Mock avatar controller for terminal-based pipeline validation."""

import asyncio
import logging
import wave
from pathlib import Path

from hai_avatar.avatar.base import AvatarController

logger = logging.getLogger(__name__)


class MockAvatarController(AvatarController):
    """Log avatar state changes and simulate action durations."""

    def __init__(self) -> None:
        self.connected = False
        self.events: list[str] = []
        self.current_expression = "neutral"

    async def connect(self) -> None:
        self.connected = True
        self._record("[Avatar] Connected (mock)")

    async def set_expression(self, expression: str) -> None:
        self.current_expression = expression
        self._record(f"[Avatar] Expression -> {expression}")

    async def trigger_gesture(self, gesture: str, intensity: float = 0.5) -> None:
        self._record(f"[Avatar] Gesture -> {gesture} (intensity={intensity:.2f})")
        if gesture != "idle":
            await asyncio.sleep(0.05)

    async def play_audio(self, audio_path: str) -> None:
        self._record(f"[Avatar] Playing audio: {audio_path}")
        await asyncio.sleep(min(0.3, self._duration_seconds(audio_path)))

    async def start_speaking(self) -> None:
        self._record("[Avatar] Speaking started")

    async def stop_speaking(self) -> None:
        self._record("[Avatar] Speaking stopped")

    async def reset_to_idle(self) -> None:
        self.current_expression = "neutral"
        self._record("[Avatar] Returned to idle")

    def _record(self, message: str) -> None:
        self.events.append(message)
        print(message)
        logger.info(message)

    def _duration_seconds(self, audio_path: str) -> float:
        path = Path(audio_path)
        if not path.exists() or path.suffix.lower() != ".wav":
            return 0.1
        try:
            with wave.open(str(path), "rb") as wav:
                return wav.getnframes() / float(wav.getframerate())
        except wave.Error:
            return 0.1
