"""End-to-end orchestration for the chat avatar pipeline."""

import logging
import time
import uuid
from pathlib import Path

from hai_avatar.avatar.base import AvatarController
from hai_avatar.config import Settings
from hai_avatar.exceptions import LLMResponseParseError, PipelineError, TTSProviderError
from hai_avatar.llm.base import LLMProvider
from hai_avatar.planner.action_planner import ActionPlanner
from hai_avatar.planner.validator import fallback_llm_response, parse_llm_avatar_response
from hai_avatar.schemas import PipelineResult
from hai_avatar.tts.base import TTSProvider

logger = logging.getLogger(__name__)


class PipelineService:
    """Run one user turn through LLM, planner, TTS, and avatar layers."""

    def __init__(
        self,
        settings: Settings,
        llm_provider: LLMProvider,
        tts_provider: TTSProvider,
        avatar_controller: AvatarController,
        action_planner: ActionPlanner,
    ) -> None:
        self.settings = settings
        self.llm_provider = llm_provider
        self.tts_provider = tts_provider
        self.avatar = avatar_controller
        self.planner = action_planner
        self._avatar_connected = False

    async def process(self, user_text: str) -> PipelineResult:
        start = time.perf_counter()
        latency_ms: dict[str, float] = {}
        warnings: list[str] = []
        clean_text = user_text.strip()
        if not clean_text:
            raise PipelineError("User text is empty.")
        if len(clean_text) > self.settings.app.max_input_chars:
            raise PipelineError(f"User text exceeds {self.settings.app.max_input_chars} characters.")

        logger.info("Pipeline request started; input_length=%s", len(clean_text))

        raw_response = ""
        t0 = time.perf_counter()
        try:
            raw_response = await self.llm_provider.generate(clean_text)
            logger.info("LLM call succeeded with provider=%s", self.settings.llm.provider)
        except Exception as exc:
            logger.exception("LLM provider failed")
            warnings.append(f"LLM failed and fallback response was used: {exc}")
        latency_ms["llm"] = self._elapsed(t0)

        t0 = time.perf_counter()
        try:
            llm_response = parse_llm_avatar_response(raw_response)
        except LLMResponseParseError as exc:
            logger.exception("LLM JSON parsing failed")
            warnings.append(f"LLM JSON parse failed and neutral fallback was used: {exc}")
            llm_response = fallback_llm_response(clean_text)
        if not llm_response.reply_text.strip():
            warnings.append("LLM returned empty reply_text; neutral fallback was used.")
            llm_response = fallback_llm_response(clean_text)
        elif len(llm_response.reply_text) > self.settings.app.max_reply_chars:
            warnings.append(f"reply_text truncated to {self.settings.app.max_reply_chars} characters.")
            llm_response = llm_response.model_copy(
                update={"reply_text": llm_response.reply_text[: self.settings.app.max_reply_chars]}
            )
        latency_ms["json_parsing"] = self._elapsed(t0)

        t0 = time.perf_counter()
        avatar_command, planner_warnings = self.planner.plan(llm_response, clean_text)
        warnings.extend(planner_warnings)
        latency_ms["action_planner"] = self._elapsed(t0)

        audio_path: str | None = None
        t0 = time.perf_counter()
        try:
            output_path = self._next_audio_path(self.settings.tts.output_dir)
            tts_result = await self.tts_provider.synthesize(
                llm_response.reply_text, avatar_command.voice_style.value, output_path
            )
            audio_path = tts_result.audio_path
            logger.info("TTS wrote audio to %s", audio_path)
        except Exception as exc:
            logger.exception("TTS failed")
            warnings.append(f"TTS failed; text response is still available: {exc}")
        latency_ms["tts"] = self._elapsed(t0)

        t0 = time.perf_counter()
        try:
            await self._ensure_avatar_connected()
            await self.avatar.set_expression(avatar_command.expression.value)
            for gesture in avatar_command.gestures:
                await self.avatar.trigger_gesture(gesture.value)
        except Exception as exc:
            logger.exception("Avatar preparation failed")
            warnings.append(f"Avatar preparation failed: {exc}")
        latency_ms["avatar_preparation"] = self._elapsed(t0)

        t0 = time.perf_counter()
        try:
            if avatar_command.pause_before_speech_ms:
                import asyncio

                await asyncio.sleep(avatar_command.pause_before_speech_ms / 1000)
            await self.avatar.start_speaking()
            if audio_path:
                await self.avatar.play_audio(audio_path)
            await self.avatar.stop_speaking()
            if self.settings.avatar.reset_after_speech:
                await self.avatar.reset_to_idle()
        except Exception as exc:
            logger.exception("Avatar playback failed")
            warnings.append(f"Avatar playback failed: {exc}")
        latency_ms["audio_playback"] = self._elapsed(t0)
        latency_ms["end_to_end"] = self._elapsed(start)

        return PipelineResult(
            user_text=clean_text,
            reply_text=llm_response.reply_text,
            avatar_command=avatar_command,
            audio_path=audio_path,
            latency_ms=latency_ms,
            warnings=warnings,
        )

    async def _ensure_avatar_connected(self) -> None:
        if not self._avatar_connected:
            await self.avatar.connect()
            self._avatar_connected = True

    def _next_audio_path(self, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir / f"{uuid.uuid4().hex}.wav"

    def _elapsed(self, started_at: float) -> float:
        return round((time.perf_counter() - started_at) * 1000, 3)
