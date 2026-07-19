"""Run one real-API pipeline turn and update the Prometheus avatar bridge."""

import asyncio
import os
import sys

from hai_avatar.app import build_pipeline
from hai_avatar.config import load_settings
from hai_avatar.logging_config import configure_logging


async def main_async(user_text: str) -> None:
    settings = load_settings()
    settings.llm.provider = "openai"
    settings.tts.provider = os.getenv("TTS_PROVIDER", "mock")
    settings.avatar.provider = "prometheus"

    api_key_name = settings.llm.api_key_env
    if not os.getenv(api_key_name):
        raise SystemExit(
            f"Missing {api_key_name}. Put your API key in .env, then rerun this script."
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
