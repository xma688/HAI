"""LLM provider interface."""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Generate raw structured avatar responses from user text."""

    @abstractmethod
    async def generate(
        self,
        user_text: str,
        system_prompt: str = "",
        conversation_history: list[dict[str, str]] | None = None,
    ) -> str:
        """Return a JSON string matching LLMAvatarResponse.

        Args:
            user_text: The user's current input text.
            system_prompt: Optional personalized system prompt for the LLM.
            conversation_history: Optional list of {"role":"user"/"assistant", "content":"..."}.
        """
