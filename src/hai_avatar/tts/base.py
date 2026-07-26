"""Text-to-speech provider interface."""

from abc import ABC, abstractmethod
from pathlib import Path

from hai_avatar.schemas import TTSResult


class TTSProvider(ABC):
    """Synthesize text into an audio file."""

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice_style: str,
        output_path: Path,
        speaking_rate: float = 1.0,
    ) -> TTSResult:
        """Create an audio file and return metadata."""
