import asyncio
from pathlib import Path
from uuid import uuid4

from hai_avatar.avatar.mock_controller import MockAvatarController
from hai_avatar.avatar.prometheus_controller import PrometheusAvatarController
from hai_avatar.tts.mock_provider import MockTTSProvider


def test_mock_tts_returns_valid_file_path():
    provider = MockTTSProvider()
    output_path = Path("assets/temp") / f"test-{uuid4().hex}.wav"
    result = asyncio.run(provider.synthesize("你好", "neutral", output_path))
    assert Path(result.audio_path).exists()
    assert result.duration_ms is not None


def test_mock_avatar_executes_command():
    avatar = MockAvatarController()

    async def run():
        await avatar.connect()
        await avatar.set_expression("soft_smile")
        await avatar.trigger_gesture("nod")
        await avatar.start_speaking()
        await avatar.stop_speaking()
        await avatar.reset_to_idle()

    asyncio.run(run())
    assert avatar.connected
    assert any("Expression" in event for event in avatar.events)
    assert avatar.current_expression == "neutral"


def test_prometheus_controller_writes_bridge_files():
    output_dir = Path("data/test_tmp/prometheus-controller")
    avatar = PrometheusAvatarController(
        output_dir=output_dir,
        model_url="https://example.com/model.model3.json",
    )

    async def run():
        await avatar.connect()
        await avatar.set_reply_text("你好", "calm")
        await avatar.set_expression("soft_smile")
        await avatar.trigger_gesture("nod")
        await avatar.start_speaking()
        await avatar.play_audio("assets/temp/mock.wav")
        await avatar.stop_speaking()

    asyncio.run(run())
    assert (output_dir / "index.html").exists()
    state = (output_dir / "avatar-state.js").read_text(encoding="utf-8")
    assert "HAI_AVATAR_STATE" in state
    assert "soft_smile" in state
