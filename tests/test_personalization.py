import asyncio
import json
from pathlib import Path
from uuid import uuid4

from hai_avatar.avatar.mock_controller import MockAvatarController
from hai_avatar.config import load_settings
from hai_avatar.llm.mock_provider import MockLLMProvider
from hai_avatar.personalization.post_processor import PostProcessor
from hai_avatar.personalization.profile_manager import ProfileManager
from hai_avatar.personalization.prompt_builder import build_personalized_system_prompt
from hai_avatar.planner.action_planner import ActionPlanner
from hai_avatar.schemas import (
    AvatarCommand,
    EmotionType,
    ExpressionType,
    GestureType,
    UserProfile,
    VoiceStyleType,
)
from hai_avatar.services.pipeline_service import PipelineService
from hai_avatar.tts.mock_provider import MockTTSProvider


def _test_dir() -> Path:
    path = Path("data") / "test_tmp" / uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    return path


def _make_personalized_pipeline(settings, tmpdir: str) -> PipelineService:
    profile_mgr = ProfileManager(profile_dir=Path(tmpdir))
    post = PostProcessor()
    return PipelineService(
        settings=settings,
        llm_provider=MockLLMProvider(),
        tts_provider=MockTTSProvider(),
        avatar_controller=MockAvatarController(),
        action_planner=ActionPlanner(enable_cooldown=False),
        profile_manager=profile_mgr,
        post_processor=post,
    )


def test_empty_profile_defaults_to_neutral_prompt():
    profile = UserProfile(user_id="test")
    prompt = build_personalized_system_prompt(profile)
    assert "请在上述画像约束下生成最合适的回复。" in prompt
    assert "Big Five" not in prompt


def test_inferred_profile_includes_big_five():
    profile = UserProfile(user_id="test")
    profile.big_five.source = "inferred"
    profile.big_five.neuroticism = 0.75
    profile.big_five.openness = 0.8
    profile.preferences.expressiveness_tolerance = 0.3
    prompt = build_personalized_system_prompt(profile)
    assert "神经质" in prompt
    assert "开放性" in prompt
    assert "支持性" in prompt.lower() or "supportive" in prompt.lower()


def test_low_expressiveness_dampens_intensity():
    post = PostProcessor()
    profile = UserProfile(user_id="test")
    profile.preferences.expressiveness_tolerance = 0.4
    command = AvatarCommand(
        emotion=EmotionType.happy,
        expression=ExpressionType.smile,
        gestures=[GestureType.wave],
        voice_style=VoiceStyleType.cheerful,
        gesture_intensity=0.8,
    )
    adjusted = post.apply(command, profile)
    assert adjusted.gesture_intensity == 0.32


def test_high_expressiveness_leaves_intensity():
    post = PostProcessor()
    profile = UserProfile(user_id="test")
    profile.preferences.expressiveness_tolerance = 0.9
    command = AvatarCommand(
        emotion=EmotionType.happy,
        expression=ExpressionType.smile,
        gestures=[GestureType.wave],
        voice_style=VoiceStyleType.cheerful,
        gesture_intensity=0.8,
    )
    adjusted = post.apply(command, profile)
    assert adjusted.gesture_intensity == 0.72


def test_gesture_frequency_minimal_caps_count():
    post = PostProcessor()
    profile = UserProfile(user_id="test")
    profile.preferences.gesture_frequency = "minimal"
    command = AvatarCommand(
        emotion=EmotionType.supportive,
        expression=ExpressionType.soft_smile,
        gestures=[GestureType.nod, GestureType.explain],
        voice_style=VoiceStyleType.calm,
    )
    adjusted = post.apply(command, profile)
    assert len(adjusted.gestures) == 1


def test_gesture_affinity_filters_unwanted_gestures():
    post = PostProcessor()
    profile = UserProfile(user_id="test")
    profile.gesture_affinity = {"wave": 0.1, "nod": 0.8, "explain": 0.5}
    command = AvatarCommand(
        emotion=EmotionType.happy,
        expression=ExpressionType.smile,
        gestures=[GestureType.wave, GestureType.nod],
        voice_style=VoiceStyleType.cheerful,
    )
    adjusted = post.apply(command, profile)
    assert GestureType.wave not in adjusted.gestures


def test_pace_adjusts_speaking_rate():
    post = PostProcessor()
    profile = UserProfile(user_id="test")
    profile.preferences.pace = "slow"
    command = AvatarCommand(
        emotion=EmotionType.neutral,
        expression=ExpressionType.neutral,
        gestures=[GestureType.idle],
        voice_style=VoiceStyleType.neutral,
        speaking_rate=1.0,
    )
    adjusted = post.apply(command, profile)
    assert adjusted.speaking_rate == 0.8


def test_profile_manager_creates_and_loads():
    tmpdir = _test_dir()
    mgr = ProfileManager(profile_dir=tmpdir)
    profile = mgr.get_or_create("user1")
    assert profile.user_id == "user1"
    assert profile.interaction_count == 0
    loaded = mgr.get_or_create("user1")
    assert loaded.user_id == "user1"


def test_profile_manager_updates_big_five_from_text():
    tmpdir = _test_dir()
    mgr = ProfileManager(profile_dir=tmpdir, learning_rate=0.1)
    profile = mgr.get_or_create("user1")
    mgr.update(profile, "我最近压力很大很焦虑", ["supportive"], ["nod"])
    assert profile.big_five.neuroticism > 0.5
    assert profile.big_five.source == "inferred"


def test_profile_manager_updates_gesture_affinity():
    tmpdir = _test_dir()
    mgr = ProfileManager(profile_dir=tmpdir)
    profile = mgr.get_or_create("user1")
    mgr.update(profile, "你好", ["happy"], ["nod", "wave"])
    assert profile.gesture_affinity.get("nod", 0) > 0.0
    assert profile.gesture_affinity.get("wave", 0) > 0.0


def test_profile_manager_self_report():
    tmpdir = _test_dir()
    mgr = ProfileManager(profile_dir=tmpdir)
    profile = mgr.get_or_create("user1")
    mgr.set_self_report(profile, {"openness": 0.8, "neuroticism": 0.6})
    assert profile.big_five.openness == 0.8
    assert profile.big_five.neuroticism == 0.6
    assert profile.big_five.source == "self_report"


def test_profile_manager_delete():
    tmpdir = _test_dir()
    mgr = ProfileManager(profile_dir=tmpdir)
    mgr.get_or_create("user1")
    assert (tmpdir / "user1.json").exists()
    mgr.delete("user1")
    assert not (tmpdir / "user1.json").exists()


def test_preferences_update_from_accumulated_big_five():
    tmpdir = _test_dir()
    mgr = ProfileManager(profile_dir=tmpdir)
    profile = mgr.get_or_create("user1")
    profile.big_five.source = "inferred"
    profile.big_five.neuroticism = 0.8
    profile.big_five.extraversion = 0.2
    profile.interaction_count = 6
    mgr._update_preferences_from_accumulated(profile)
    assert profile.preferences.expressiveness_tolerance <= 0.7
    assert profile.preferences.gesture_frequency == "minimal"
    assert profile.preferences.pace == "slow"


def test_mock_pipeline_with_personalization_enabled():
    tmpdir = _test_dir()
    settings = load_settings()
    settings.personalization.enabled = True
    settings.personalization.profile_dir = str(tmpdir)
    settings.tts.output_dir = tmpdir / "audio"
    pipeline = _make_personalized_pipeline(settings, str(tmpdir))
    result = asyncio.run(pipeline.process("我最近项目压力有点大"))
    assert result.reply_text
    assert result.avatar_command.emotion in set(EmotionType)
    assert "profile_load" in result.latency_ms
    assert "post_processor" in result.latency_ms
    assert "state_update" in result.latency_ms


def test_mock_pipeline_with_personalization_disabled():
    settings = load_settings()
    settings.personalization.enabled = False
    pipeline = PipelineService(
        settings=settings,
        llm_provider=MockLLMProvider(),
        tts_provider=MockTTSProvider(),
        avatar_controller=MockAvatarController(),
        action_planner=ActionPlanner(enable_cooldown=False),
        profile_manager=None,
        post_processor=None,
    )
    result = asyncio.run(pipeline.process("你好！"))
    assert result.reply_text
    assert "profile_load" not in result.latency_ms


def test_mock_provider_accepts_system_prompt():
    provider = MockLLMProvider()
    response = asyncio.run(provider.generate("你好", system_prompt="用户偏好正式规范的表达方式"))
    data = json.loads(response)
    assert "reply_text" in data


def test_mock_provider_prompt_modifies_expression():
    provider = MockLLMProvider()
    response = asyncio.run(
        provider.generate(
            "太惊讶了！",
            system_prompt="该用户对夸张的表情动作接受度较低，请优先使用 neutral 或 soft_smile 表情"
        )
    )
    data = json.loads(response)
    assert data["expression"] in ("neutral", "soft_smile", "concerned")


def test_mock_provider_uses_conversation_history():
    provider = MockLLMProvider()
    history = [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": '{"gestures":["wave","nod"]}'},
    ]
    response = asyncio.run(provider.generate("你好！", conversation_history=history))
    data = json.loads(response)
    assert "reply_text" in data


def test_mock_pipeline_conversation_history_accumulates():
    tmpdir = _test_dir()
    settings = load_settings()
    settings.personalization.profile_dir = str(tmpdir)
    settings.tts.output_dir = tmpdir / "audio"
    pipeline = _make_personalized_pipeline(settings, str(tmpdir))
    result1 = asyncio.run(pipeline.process("你好！", user_id="hist_test"))
    assert result1.reply_text
    result2 = asyncio.run(pipeline.process("谢谢！", user_id="hist_test"))
    assert result2.reply_text
    history = pipeline.conversation_service.last_turns(5)
    assert len(history) >= 2
