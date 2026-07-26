"""Run one real-API pipeline turn and update the Prometheus avatar bridge."""

import asyncio
import os
import sys

from hai_avatar.app import build_pipeline
from hai_avatar.config import load_settings
from hai_avatar.logging_config import configure_logging


def _select_available_api_key_env() -> str | None:
    for name in ("OPENCODE_GO_API_KEY", "DEEPSEEK_API_KEY", "OPENAI_API_KEY"):
        if os.getenv(name):
            return name
    return None


async def main_async(user_text: str) -> None:
    settings = load_settings()
    settings.llm.provider = "openai"
    settings.tts.provider = "moss_tts" #os.getenv("TTS_PROVIDER", "mock")
    settings.avatar.provider = "prometheus"

    api_key_name = _select_available_api_key_env() or settings.llm.api_key_env
    settings.llm.api_key_env = api_key_name
    if not os.getenv(api_key_name):
        raise SystemExit(
            "Missing API key. Put one of OPENCODE_GO_API_KEY, DEEPSEEK_API_KEY, or OPENAI_API_KEY "
            "in .env, then rerun this script."
        )
    if api_key_name != "OPENCODE_GO_API_KEY" and not os.getenv("LLM_BASE_URL"):
        raise SystemExit(
            f"{api_key_name} is set, but LLM_BASE_URL is not. Add the OpenAI-compatible endpoint to .env."
        )

    pipeline = build_pipeline(settings)
    result = await pipeline.process(user_text)
    print("\n[Real API + Prometheus result]")
    print(f"reply: {result.reply_text}")
    print(f"command: {result.avatar_command.model_dump(mode='json')}")
    print(f"audio: {result.audio_path}")
    print("open: http://127.0.0.1:8010")


if __name__ == "__main__":
    configure_logging()
    text = " ".join(sys.argv[1:]).strip() or "你好，请用中文自然地回复我。"
    asyncio.run(main_async(text))
