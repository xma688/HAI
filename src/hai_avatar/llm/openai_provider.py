"""Placeholder for the Phase 4 real LLM provider."""

from hai_avatar.exceptions import LLMProviderError
from hai_avatar.llm.base import LLMProvider


class OpenAIProvider(LLMProvider):
    """Deferred until Phase 4 to avoid unverified API assumptions."""

    async def generate(self, user_text: str) -> str:
        raise LLMProviderError("OpenAIProvider is not implemented in Phase 0-2.")
