"""Placeholder for the Phase 6 VTube Studio controller."""

from hai_avatar.avatar.base import AvatarController
from hai_avatar.exceptions import AvatarConnectionError


class VTubeStudioController(AvatarController):
    """Deferred until protocol and dependency validation in Phase 6."""

    async def connect(self) -> None:
        raise AvatarConnectionError("VTubeStudioController is not implemented in Phase 0-2.")

    async def set_expression(self, expression: str) -> None:
        raise AvatarConnectionError("VTubeStudioController is not implemented in Phase 0-2.")

    async def trigger_gesture(self, gesture: str) -> None:
        raise AvatarConnectionError("VTubeStudioController is not implemented in Phase 0-2.")

    async def play_audio(self, audio_path: str) -> None:
        raise AvatarConnectionError("VTubeStudioController is not implemented in Phase 0-2.")

    async def start_speaking(self) -> None:
        raise AvatarConnectionError("VTubeStudioController is not implemented in Phase 0-2.")

    async def stop_speaking(self) -> None:
        raise AvatarConnectionError("VTubeStudioController is not implemented in Phase 0-2.")

    async def reset_to_idle(self) -> None:
        raise AvatarConnectionError("VTubeStudioController is not implemented in Phase 0-2.")
