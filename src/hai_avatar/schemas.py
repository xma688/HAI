"""Pydantic models and finite control-label enums."""

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class EmotionType(str, Enum):
    neutral = "neutral"
    happy = "happy"
    supportive = "supportive"
    thoughtful = "thoughtful"
    confused = "confused"
    surprised = "surprised"
    serious = "serious"
    apologetic = "apologetic"


class ExpressionType(str, Enum):
    neutral = "neutral"
    smile = "smile"
    soft_smile = "soft_smile"
    thinking = "thinking"
    confused = "confused"
    surprised = "surprised"
    concerned = "concerned"
    serious = "serious"


class GestureType(str, Enum):
    idle = "idle"
    nod = "nod"
    wave = "wave"
    head_tilt = "head_tilt"
    think = "think"
    explain = "explain"
    agree = "agree"
    small_bow = "small_bow"


class VoiceStyleType(str, Enum):
    neutral = "neutral"
    calm = "calm"
    cheerful = "cheerful"
    gentle = "gentle"
    serious = "serious"
    apologetic = "apologetic"


class LLMAvatarResponse(BaseModel):
    """Raw structured response requested from an LLM provider."""

    reply_text: str
    emotion: str
    expression: str
    gestures: list[str] = Field(default_factory=list)
    voice_style: str
    pause_before_speech_ms: int = 0

    @field_validator("pause_before_speech_ms")
    @classmethod
    def non_negative_pause(cls, value: int) -> int:
        return max(0, value)


class AvatarCommand(BaseModel):
    """Validated and normalized control command sent to an avatar."""

    emotion: EmotionType
    expression: ExpressionType
    gestures: list[GestureType] = Field(default_factory=lambda: [GestureType.idle])
    voice_style: VoiceStyleType
    gesture_intensity: float = Field(default=0.5, ge=0.0, le=1.0)
    speaking_rate: float = Field(default=1.0, ge=0.5, le=2.0)
    pause_before_speech_ms: int = 0


class TTSResult(BaseModel):
    """Result returned by a TTS provider."""

    audio_path: str
    duration_ms: int | None = None
    sample_rate: int | None = None


class PipelineResult(BaseModel):
    """Complete result returned from one pipeline turn."""

    user_text: str
    reply_text: str
    avatar_command: AvatarCommand
    audio_path: str | None
    latency_ms: dict[str, float]
    warnings: list[str] = Field(default_factory=list)
