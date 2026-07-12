import asyncio
from pathlib import Path
from uuid import uuid4

from hai_avatar.avatar.mock_controller import MockAvatarController
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
