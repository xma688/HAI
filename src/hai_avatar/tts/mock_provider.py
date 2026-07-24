"""Mock TTS provider that writes a small WAV file."""

import math
import struct
import wave
from pathlib import Path

from hai_avatar.schemas import TTSResult
from hai_avatar.tts.base import TTSProvider


class MockTTSProvider(TTSProvider):
    """Generate a short tone/silence WAV so the pipeline has a real file."""

    sample_rate = 16_000

    async def synthesize(
        self,
        text: str,
        voice_style: str,
        output_path: Path,
        speaking_rate: float = 1.0,
    ) -> TTSResult:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        safe_rate = max(0.5, min(2.0, speaking_rate))
        duration_ms = int(min(3000, max(700, len(text) * 55)) / safe_rate)
        frequency = {
            "cheerful": 660,
            "gentle": 440,
            "calm": 392,
            "serious": 330,
            "apologetic": 360,
        }.get(voice_style, 520)
        frames = int(self.sample_rate * duration_ms / 1000)

        with wave.open(str(output_path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(self.sample_rate)
            for index in range(frames):
                envelope = min(1.0, index / 800, (frames - index) / 800)
                value = int(9000 * envelope * math.sin(2 * math.pi * frequency * index / self.sample_rate))
                wav.writeframesraw(struct.pack("<h", value))

        return TTSResult(audio_path=str(output_path), duration_ms=duration_ms, sample_rate=self.sample_rate)


def cleanup_old_audio(output_dir: Path, max_age_seconds: int = 3600) -> int:
    """Remove old generated WAV files from the mock output directory."""

    import time

    if not output_dir.exists():
        return 0
    removed = 0
    cutoff = time.time() - max_age_seconds
    for path in output_dir.glob("*.wav"):
        if path.stat().st_mtime < cutoff:
            path.unlink()
            removed += 1
    return removed
