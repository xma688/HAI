"""End-to-end orchestration for the chat avatar pipeline."""

import asyncio
import logging
import time
import uuid
from pathlib import Path
from typing import Optional

from hai_avatar.avatar.base import AvatarController
from hai_avatar.config import Settings
from hai_avatar.exceptions import LLMResponseParseError, PipelineError, TTSProviderError
from hai_avatar.llm.base import LLMProvider
from hai_avatar.personalization.post_processor import PostProcessor
from hai_avatar.personalization.profile_manager import ProfileManager
from hai_avatar.personalization.prompt_builder import build_personalized_system_prompt
from hai_avatar.planner.action_planner import ActionPlanner
from hai_avatar.planner.validator import fallback_llm_response, parse_llm_avatar_response
from hai_avatar.schemas import PipelineResult, UserProfile
from hai_avatar.services.conversation_service import ConversationService
from hai_avatar.tts.base import TTSProvider

logger = logging.getLogger(__name__)


class PipelineService:
    def __init__(
        self,
        settings: Settings,
        llm_provider: LLMProvider,
        tts_provider: TTSProvider,
        avatar_controller: AvatarController,
        action_planner: ActionPlanner,
        profile_manager: Optional[ProfileManager] = None,
        post_processor: Optional[PostProcessor] = None,
        conversation_service: Optional[ConversationService] = None,
    ) -> None:
        self.settings = settings
        self.llm_provider = llm_provider
        self.tts_provider = tts_provider
        self.avatar = avatar_controller
        self.planner = action_planner
        self.profile_manager = profile_manager
        self.post_processor = post_processor
        self.conversation_service = conversation_service or ConversationService()
        self._avatar_connected = False

    async def process(self, user_text: str, user_id: str = "default") -> PipelineResult:
        start = time.perf_counter()
        latency_ms: dict[str, float] = {}
        warnings: list[str] = []
        clean_text = user_text.strip()
        if not clean_text:
            raise PipelineError("User text is empty.")
        if len(clean_text) > self.settings.app.max_input_chars:
            raise PipelineError(f"User text exceeds {self.settings.app.max_input_chars} characters.")

        logger.info("Pipeline request started; input_length=%s user_id=%s", len(clean_text), user_id)

        if self._personalization_enabled:
            t0 = time.perf_counter()
            user_profile = self._load_profile(user_id)
            personalized_prompt = self._build_personalized_prompt(user_profile)
            latency_ms["profile_load"] = self._elapsed(t0)
        else:
            user_profile = UserProfile(user_id=user_id)
            personalized_prompt = ""

        t0 = time.perf_counter()
        history = self._build_conversation_history()
        latency_ms["history_build"] = self._elapsed(t0)

        raw_response = ""
        t0 = time.perf_counter()
        try:
            raw_response = await self.llm_provider.generate(
                clean_text,
                system_prompt=personalized_prompt,
                conversation_history=history,
            )
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

        t0 = time.perf_counter()
        if self.post_processor and self._personalization_enabled:
            avatar_command = self.post_processor.apply(avatar_command, user_profile)
            latency_ms["post_processor"] = self._elapsed(t0)
        else:
            latency_ms["post_processor"] = 0

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

        t0 = time.perf_counter()
        self.conversation_service.add_turn(clean_text, llm_response.reply_text)
        self._update_profile(user_profile, clean_text, avatar_command)
        latency_ms["state_update"] = self._elapsed(t0)

        return PipelineResult(
            user_text=clean_text,
            reply_text=llm_response.reply_text,
            avatar_command=avatar_command,
            audio_path=audio_path,
            latency_ms=latency_ms,
            warnings=warnings,
        )

    def _build_conversation_history(self) -> list[dict[str, str]]:
        history: list[dict[str, str]] = []
        for user, assistant in self.conversation_service.last_turns(3):
            history.append({"role": "user", "content": user})
            history.append({"role": "assistant", "content": assistant})
        return history

    def _load_profile(self, user_id: str) -> UserProfile:
        if not self.profile_manager or not self._personalization_enabled:
            return UserProfile(user_id=user_id)
        return self.profile_manager.get_or_create(user_id)

    def _build_personalized_prompt(self, profile: UserProfile) -> str:
        if not self._personalization_enabled or profile.interaction_count < 1:
            return ""
        return build_personalized_system_prompt(profile)

    def _update_profile(self, profile: UserProfile, user_text: str, command) -> None:
        if not self.profile_manager or not self._personalization_enabled:
            return
        emotions_used = [command.emotion.value]
        gestures_used = [g.value for g in command.gestures]
        self.profile_manager.update(profile, user_text, emotions_used, gestures_used)

    @property
    def _personalization_enabled(self) -> bool:
        return self.settings.personalization.enabled and self.profile_manager is not None

    async def _ensure_avatar_connected(self) -> None:
        if not self._avatar_connected:
            await self.avatar.connect()
            self._avatar_connected = True

    def _next_audio_path(self, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir / f"{uuid.uuid4().hex}.wav"

    def _elapsed(self, started_at: float) -> float:
        return round((time.perf_counter() - started_at) * 1000, 3)
