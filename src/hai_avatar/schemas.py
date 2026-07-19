"""Pydantic models and finite control-label enums."""

from __future__ import annotations

from datetime import datetime, timezone
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
    gesture_intensity: float = Field(default=0.5, ge=0.0, le=1.0)
    speaking_rate: float = Field(default=1.0, ge=0.5, le=2.0)
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
    raw_llm_output: str | None = None
    avatar_command_before_post: AvatarCommand | None = None
    user_profile: UserProfile | None = None


class BigFiveTraits(BaseModel):
    openness: float = Field(default=0.5, ge=0.0, le=1.0)
    conscientiousness: float = Field(default=0.5, ge=0.0, le=1.0)
    extraversion: float = Field(default=0.5, ge=0.0, le=1.0)
    agreeableness: float = Field(default=0.5, ge=0.0, le=1.0)
    neuroticism: float = Field(default=0.5, ge=0.0, le=1.0)
    source: str = Field(default="default")


class CommunicationPreferences(BaseModel):
    formality: str = Field(default="neutral")
    expressiveness_tolerance: float = Field(default=0.7, ge=0.0, le=1.0)
    gesture_frequency: str = Field(default="moderate")
    pace: str = Field(default="moderate")


class UserProfile(BaseModel):
    user_id: str = Field(default="default")
    big_five: BigFiveTraits = Field(default_factory=BigFiveTraits)
    preferences: CommunicationPreferences = Field(default_factory=CommunicationPreferences)
    gesture_affinity: dict[str, float] = Field(default_factory=dict)
    interaction_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
