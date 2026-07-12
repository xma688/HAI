"""LLM provider interface."""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Generate raw structured avatar responses from user text."""

    @abstractmethod
    async def generate(self, user_text: str) -> str:
        """Return a JSON string matching LLMAvatarResponse."""
