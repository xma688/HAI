"""Placeholder for the Phase 5 Edge TTS provider."""

from pathlib import Path

from hai_avatar.exceptions import TTSProviderError
from hai_avatar.schemas import TTSResult
from hai_avatar.tts.base import TTSProvider


class EdgeTTSProvider(TTSProvider):
    """Deferred until Phase 5 after dependency and voice behavior validation."""

    async def synthesize(self, text: str, voice_style: str, output_path: Path) -> TTSResult:
        raise TTSProviderError("EdgeTTSProvider is not implemented in Phase 0-2.")
