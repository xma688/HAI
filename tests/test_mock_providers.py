import asyncio
import time
import wave
from pathlib import Path
from uuid import uuid4

from hai_avatar.avatar.mock_controller import MockAvatarController
from hai_avatar.avatar.prometheus_controller import PrometheusAvatarController
from hai_avatar.tts.edge_tts_provider import _resolve_rate_percent
from hai_avatar.tts.mock_provider import MockTTSProvider


def test_mock_tts_returns_valid_file_path():
    provider = MockTTSProvider()
    output_path = Path("assets/temp") / f"test-{uuid4().hex}.wav"
    result = asyncio.run(provider.synthesize("你好", "neutral", output_path))
    assert Path(result.audio_path).exists()
    assert result.duration_ms is not None


def test_edge_tts_rate_stays_within_narrow_range():
    assert _resolve_rate_percent(0.5, "neutral") == -10
    assert _resolve_rate_percent(0.9, "calm") == -10
    assert _resolve_rate_percent(1.0, "neutral") == 0
    assert _resolve_rate_percent(1.1, "cheerful") == 10
    assert _resolve_rate_percent(2.0, "neutral") == 10


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


def test_prometheus_controller_writes_bridge_files(tmp_path):
    output_dir = tmp_path / "prometheus-controller"
    audio_path = tmp_path / "mock.wav"
    with wave.open(str(audio_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16_000)
        wav_file.writeframes(b"\x00\x00" * 800)
    avatar = PrometheusAvatarController(
        output_dir=output_dir,
        model_url="https://example.com/model.model3.json",
    )

    async def run():
        await avatar.connect()
        await avatar.set_reply_text("你好", "calm")
        await avatar.set_expression("soft_smile")
        await avatar.trigger_gesture("nod", intensity=0.8)
        await avatar.start_speaking()
        started_at = time.perf_counter()
        await avatar.play_audio(str(audio_path))
        assert time.perf_counter() - started_at < 0.04
        await avatar.stop_speaking()
        assert avatar.state["speaking"] is True
        assert avatar.state["gestures"] == ["nod"]
        assert avatar.state["gesture_intensity"] == 0.8
        assert avatar.state["audio_url"].startswith("./audio/")
        await avatar.reset_to_idle()
        assert avatar.state["expression"] == "soft_smile"
        await asyncio.sleep(0.08)
        assert avatar.state["speaking"] is False
        assert avatar.state["expression"] == "neutral"
        assert avatar.state["reply_text"] == "你好"
        await avatar.clear_session_state()

    asyncio.run(run())
    assert (output_dir / "index.html").exists()
    bridge_html = (output_dir / "index.html").read_text(encoding="utf-8")
    assert "modelBaseDimensions" in bridge_html
    assert "ResizeObserver" in bridge_html
    assert "app.screen?.width" in bridge_html
    assert "* 0.70" in bridge_html
    assert "visibilitychange" in bridge_html
    assert "document.visibilityState" in bridge_html
    assert "navigator.locks?.request" in bridge_html
    assert "hai-avatar-audio-playback" in bridge_html
    assert "dataset.audioState = 'suppressed-locked'" in bridge_html
    state = (output_dir / "avatar-state.js").read_text(encoding="utf-8")
    assert "HAI_AVATAR_STATE" in state
    assert "session cleared" in state
    assert avatar.state["gestures"] == []
    assert avatar.state["reply_text"] == ""
    assert avatar.state["audio_url"] is None
    assert avatar.state["events"] == ["session cleared"]
