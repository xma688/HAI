"""Custom exceptions for the chat avatar pipeline."""


class PipelineError(Exception):
    """Base error raised by pipeline orchestration."""


class LLMProviderError(PipelineError):
    """Raised when an LLM provider cannot generate a response."""


class LLMResponseParseError(PipelineError):
    """Raised when structured LLM output cannot be parsed."""


class TTSProviderError(PipelineError):
    """Raised when text-to-speech synthesis fails."""


class AvatarConnectionError(PipelineError):
    """Raised when an avatar backend cannot be reached."""


class AvatarCommandError(PipelineError):
    """Raised when an avatar command cannot be executed."""
