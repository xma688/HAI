"""Avatar controller interface."""

from abc import ABC, abstractmethod


class AvatarController(ABC):
    """Backend-agnostic avatar command interface."""

    @abstractmethod
    async def connect(self) -> None:
        """Connect to the avatar backend."""

    @abstractmethod
    async def set_expression(self, expression: str) -> None:
        """Set avatar expression."""

    @abstractmethod
    async def trigger_gesture(self, gesture: str) -> None:
        """Trigger one gesture."""

    @abstractmethod
    async def play_audio(self, audio_path: str) -> None:
        """Play or simulate playing an audio file."""

    @abstractmethod
    async def start_speaking(self) -> None:
        """Mark the avatar as speaking."""

    @abstractmethod
    async def stop_speaking(self) -> None:
        """Mark the avatar as no longer speaking."""

    @abstractmethod
    async def reset_to_idle(self) -> None:
        """Return the avatar to idle state."""
