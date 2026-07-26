"""Edge TTS provider using Microsoft Edge's free text-to-speech."""

import asyncio
import logging
import wave
from pathlib import Path

from hai_avatar.schemas import TTSResult
from hai_avatar.tts.base import TTSProvider

logger = logging.getLogger(__name__)

_VOICE_STYLE_PARAMS: dict[str, dict[str, str]] = {
    "calm": {"rate": "-10%", "pitch": "-2Hz"},
    "cheerful": {"rate": "+10%", "pitch": "+5Hz"},
    "gentle": {"rate": "-5%", "pitch": "+0Hz"},
    "serious": {"rate": "-5%", "pitch": "-3Hz"},
    "apologetic": {"rate": "-10%", "pitch": "-5Hz"},
    "neutral": {"rate": "+0%", "pitch": "+0Hz"},
}


class EdgeTTSProvider(TTSProvider):
    def __init__(self, voice: str = "zh-CN-XiaoxiaoNeural") -> None:
        self._voice = voice

    async def synthesize(self, text: str, voice_style: str, output_path: Path) -> TTSResult:
        import edge_tts

        params = _VOICE_STYLE_PARAMS.get(voice_style, _VOICE_STYLE_PARAMS["neutral"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = output_path.with_suffix(".mp3")

        communicate = edge_tts.Communicate(
            text=text,
            voice=self._voice,
            rate=params["rate"],
            pitch=params["pitch"],
        )
        await communicate.save(str(tmp_path))
        logger.info("Edge TTS saved to %s", tmp_path)

        duration_ms = self._convert_to_wav(tmp_path, output_path)
        tmp_path.unlink(missing_ok=True)

        return TTSResult(audio_path=str(output_path), duration_ms=duration_ms)

    @staticmethod
    def _convert_to_wav(mp3_path: Path, wav_path: Path) -> int:
        import subprocess
        import sys

        try:
            subprocess.run(
                [
                    "ffmpeg", "-y", "-loglevel", "error",
                    "-i", str(mp3_path),
                    "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
                    str(wav_path),
                ],
                check=True,
                capture_output=True,
                timeout=30,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            wav_path.parent.mkdir(parents=True, exist_ok=True)
            wav_path.write_bytes(mp3_path.read_bytes())
            logger.warning("ffmpeg not found; saved raw mp3 as %s", wav_path)

        try:
            with wave.open(str(wav_path), "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                return int(frames / rate * 1000) if rate else 0
        except (wave.Error, EOFError):
            return 0
