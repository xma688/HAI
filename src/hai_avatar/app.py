"""Application factory for Phase 0-2 mock components."""

from hai_avatar.avatar.mock_controller import MockAvatarController
from hai_avatar.config import load_settings
from hai_avatar.llm.mock_provider import MockLLMProvider
from hai_avatar.planner.action_planner import ActionPlanner
from hai_avatar.services.pipeline_service import PipelineService
from hai_avatar.tts.mock_provider import MockTTSProvider


def build_mock_pipeline() -> PipelineService:
    """Create the complete mock pipeline from configuration."""

    settings = load_settings()
    planner = ActionPlanner(
        max_gestures=settings.planner.max_gestures,
        enable_cooldown=settings.planner.enable_cooldown,
    )
    return PipelineService(
        settings=settings,
        llm_provider=MockLLMProvider(),
        tts_provider=MockTTSProvider(),
        avatar_controller=MockAvatarController(),
        action_planner=planner,
    )
