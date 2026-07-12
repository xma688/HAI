import asyncio
import json
from pathlib import Path

from hai_avatar.avatar.mock_controller import MockAvatarController
from hai_avatar.config import load_settings
from hai_avatar.llm.base import LLMProvider
from hai_avatar.planner.action_planner import ActionPlanner
from hai_avatar.services.pipeline_service import PipelineService
from hai_avatar.app import build_mock_pipeline
from hai_avatar.schemas import EmotionType, ExpressionType, VoiceStyleType
from hai_avatar.tts.mock_provider import MockTTSProvider


class EmptyReplyLLMProvider(LLMProvider):
    async def generate(self, user_text: str) -> str:
        return json.dumps(
            {
                "reply_text": "",
                "emotion": "happy",
                "expression": "smile",
                "gestures": ["wave"],
                "voice_style": "cheerful",
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
