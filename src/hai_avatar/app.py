"""Application factory for building pipeline components from configuration."""

from pathlib import Path

from hai_avatar.avatar.base import AvatarController
from hai_avatar.avatar.mock_controller import MockAvatarController
from hai_avatar.avatar.prometheus_controller import PrometheusAvatarController
from hai_avatar.config import PROJECT_ROOT, Settings, load_settings
from hai_avatar.llm.base import LLMProvider
from hai_avatar.llm.mock_provider import MockLLMProvider
from hai_avatar.llm.openai_provider import OpenAIProvider
from hai_avatar.personalization.post_processor import PostProcessor
from hai_avatar.personalization.profile_manager import ProfileManager
from hai_avatar.planner.action_planner import ActionPlanner
from hai_avatar.services.conversation_service import ConversationService
from hai_avatar.services.pipeline_service import PipelineService
from hai_avatar.tts.base import TTSProvider
from hai_avatar.tts.mock_provider import MockTTSProvider


def build_mock_pipeline() -> PipelineService:
    """Create the complete mock pipeline from configuration."""
    return _build_pipeline(force_mock=True)


def build_pipeline(settings: Settings | None = None) -> PipelineService:
    """Create the pipeline based on configuration settings."""
    return _build_pipeline(settings=settings)


def _build_pipeline(
    settings: Settings | None = None,
    force_mock: bool = False,
) -> PipelineService:
    settings = settings or load_settings()
    if force_mock:
        settings = settings.model_copy(deep=True)
        settings.llm.provider = "mock"
        settings.tts.provider = "mock"
        settings.avatar.provider = "mock"
    provider_name = "mock" if force_mock else settings.llm.provider
    tts_provider_name = "mock" if force_mock else settings.tts.provider
    avatar_provider_name = "mock" if force_mock else settings.avatar.provider

    llm_provider = _create_llm_provider(provider_name, settings)
    tts_provider = _create_tts_provider(tts_provider_name, settings)
    avatar_controller = _create_avatar_controller(avatar_provider_name, settings)
    conversation_service = ConversationService()

    planner = ActionPlanner(
        max_gestures=settings.planner.max_gestures,
        enable_cooldown=settings.planner.enable_cooldown,
    )

    profile_dir = Path(settings.personalization.profile_dir)
    if not profile_dir.is_absolute():
        profile_dir = PROJECT_ROOT / profile_dir
    profile_manager = ProfileManager(
        profile_dir=profile_dir,
        learning_rate=settings.personalization.big_five_learning_rate,
        affinity_decay=settings.personalization.gesture_affinity_decay,
    )
    post_processor = PostProcessor(max_gestures_fallback=settings.planner.max_gestures)

    return PipelineService(
        settings=settings,
        llm_provider=llm_provider,
        tts_provider=tts_provider,
        avatar_controller=avatar_controller,
        action_planner=planner,
        profile_manager=profile_manager,
        post_processor=post_processor,
        conversation_service=conversation_service,
    )


def _create_llm_provider(provider_name: str, settings: Settings) -> LLMProvider:
    if provider_name == "mock":
        return MockLLMProvider()
    if provider_name == "openai":
        return OpenAIProvider(settings)
    raise ValueError(f"Unknown LLM provider: {provider_name}")


def _create_tts_provider(provider_name: str, settings: Settings) -> TTSProvider:
    if provider_name == "mock":
        return MockTTSProvider()
    if provider_name == "edge_tts":
        from hai_avatar.tts.edge_tts_provider import EdgeTTSProvider

        return EdgeTTSProvider(
            voice=settings.tts.voice,
            timeout_seconds=settings.tts.timeout_seconds,
        )
    if provider_name == "moss_tts":
        from hai_avatar.tts.moss_tts_provider import MossTTSProvider

        return MossTTSProvider(timeout_seconds=max(120, settings.tts.timeout_seconds))
    raise ValueError(f"Unknown TTS provider: {provider_name}")


def _create_avatar_controller(provider_name: str, settings: Settings) -> AvatarController:
    if provider_name == "mock":
        return MockAvatarController()
    if provider_name == "prometheus":
        output_dir = settings.avatar.prometheus_output_dir
        if not output_dir.is_absolute():
            output_dir = PROJECT_ROOT / output_dir
        return PrometheusAvatarController(
            output_dir=output_dir,
            model_url=settings.avatar.prometheus_model_url,
        )
    raise ValueError(f"Unknown Avatar provider: {provider_name}")
