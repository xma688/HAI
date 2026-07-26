import asyncio
import json
from pathlib import Path

from hai_avatar.avatar.mock_controller import MockAvatarController
from hai_avatar.config import load_settings
from hai_avatar.llm.base import LLMProvider
from hai_avatar.planner.action_planner import ActionPlanner
from hai_avatar.services.pipeline_service import PipelineService
from hai_avatar.app import build_mock_pipeline, build_pipeline
from hai_avatar.schemas import EmotionType, ExpressionType, VoiceStyleType
from hai_avatar.tts.mock_provider import MockTTSProvider


class FailingTTSProvider(MockTTSProvider):
    async def synthesize(self, *args, **kwargs):
        raise RuntimeError("synthetic TTS failure")


class EmptyReplyLLMProvider(LLMProvider):
    async def generate(
        self,
        user_text: str,
        system_prompt: str = "",
        conversation_history: list[dict[str, str]] | None = None,
    ) -> str:
        return json.dumps(
            {
                "reply_text": "",
                "emotion": "happy",
                "expression": "smile",
                "gestures": ["wave"],
                "voice_style": "cheerful",
                "gesture_intensity": 0.5,
                "speaking_rate": 1.0,
            },
            ensure_ascii=False,
        )


def test_mock_pipeline_completes_one_turn():
    pipeline = build_mock_pipeline()
    result = asyncio.run(pipeline.process("我最近项目压力有点大，不知道怎么开始。"))
    assert result.reply_text
    assert result.avatar_command.emotion in set(EmotionType)
    assert result.avatar_command.expression in set(ExpressionType)
    assert result.avatar_command.voice_style in set(VoiceStyleType)
    assert len(result.avatar_command.gestures) <= 2
    assert result.avatar_command.emotion == EmotionType.supportive
    assert result.audio_path is not None
    assert Path(result.audio_path).exists()
    assert "end_to_end" in result.latency_ms


def test_pipeline_reports_real_processing_stages_in_order():
    pipeline = build_mock_pipeline()
    stages: list[str] = []
    reply_payloads: list[str] = []

    async def collect(stage: str, payload: dict):
        stages.append(stage)
        if stage == "reply":
            reply_payloads.append(payload["reply_text"])

    result = asyncio.run(
        pipeline.process("今天有点累。", progress_callback=collect)
    )

    assert stages == ["understanding", "reply", "voice", "performance", "complete"]
    assert reply_payloads == [result.reply_text]


def test_mock_pipeline_scenarios_complete():
    cases = [
        "你好！",
        "谢谢你的帮助，再见。",
        "我不太明白这个概念，你能解释一下吗？",
        "对不起，我刚才可能说错了。",
        "这真是个令人惊讶的结果。",
    ]
    for text in cases:
        pipeline = build_mock_pipeline()
        result = asyncio.run(pipeline.process(text))
        assert result.reply_text
        assert len(result.avatar_command.gestures) <= 2
        assert result.audio_path is not None


def test_empty_reply_text_uses_fallback():
    settings = load_settings()
    pipeline = PipelineService(
        settings=settings,
        llm_provider=EmptyReplyLLMProvider(),
        tts_provider=MockTTSProvider(),
        avatar_controller=MockAvatarController(),
        action_planner=ActionPlanner(enable_cooldown=False),
    )
    result = asyncio.run(pipeline.process("你好"))
    assert result.reply_text
    assert result.avatar_command.emotion == EmotionType.neutral
    assert any("empty reply_text" in warning for warning in result.warnings)


def test_tts_failure_does_not_return_mock_beep():
    settings = load_settings()
    pipeline = PipelineService(
        settings=settings,
        llm_provider=EmptyReplyLLMProvider(),
        tts_provider=FailingTTSProvider(),
        avatar_controller=MockAvatarController(),
        action_planner=ActionPlanner(enable_cooldown=False),
    )
    result = asyncio.run(pipeline.process("你好"))
    assert result.audio_path is None
    assert any("voice output is unavailable" in warning for warning in result.warnings)


def test_build_pipeline_creates_mock_by_default():
    pipeline = build_pipeline()
    assert pipeline is not None
    result = asyncio.run(pipeline.process("你好"))
    assert result.reply_text


def test_build_mock_pipeline_still_works():
    pipeline = build_mock_pipeline()
    result = asyncio.run(pipeline.process("你好"))
    assert result.reply_text
