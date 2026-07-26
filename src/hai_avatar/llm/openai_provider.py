"""OpenAI-compatible LLM provider with retry and structured-output prompting."""

import logging
import os
from typing import Optional

from openai import AsyncOpenAI

from hai_avatar.config import PROJECT_ROOT, Settings
from hai_avatar.exceptions import LLMProviderError
from hai_avatar.llm.base import LLMProvider

logger = logging.getLogger(__name__)


def _load_system_prompt() -> str:
    path = PROJECT_ROOT / "config" / "llm_system_prompt.txt"
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return ""


class OpenAIProvider(LLMProvider):
    def __init__(self, settings: Settings) -> None:
        api_key = os.getenv(settings.llm.api_key_env, "")
        if not api_key:
            raise LLMProviderError(
                f"API key not found. Set {settings.llm.api_key_env} in environment or .env file."
            )
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=settings.llm.base_url,
            timeout=float(settings.llm.timeout_seconds),
            max_retries=settings.llm.max_retries,
        )
        self._model = settings.llm.model
        self._temperature = settings.llm.temperature
        self._base_system_prompt = _load_system_prompt()

    async def generate(
        self,
        user_text: str,
        system_prompt: str = "",
        conversation_history: list[dict[str, str]] | None = None,
    ) -> str:
        system_content = self._base_system_prompt.replace("{user_profile_context}", system_prompt)
        if not system_prompt.strip():
            system_content = system_content.replace("{user_profile_context}", "").strip()
            if system_content.endswith("\n"):
                system_content = system_content.rstrip("\n")

        messages: list[dict[str, str]] = [{"role": "system", "content": system_content}]
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_text})

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=self._temperature,
            )
            content: Optional[str] = response.choices[0].message.content
            if content is None:
                raise LLMProviderError(f"{self._model} returned empty response.")
            logger.debug("LLM call success model=%s tokens=%s", self._model, response.usage)
            return content
        except Exception as exc:
            raise LLMProviderError(f"LLM call to {self._model} failed: {exc}") from exc
