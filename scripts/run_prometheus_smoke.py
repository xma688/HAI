"""Run one mock pipeline turn using the Prometheus browser bridge avatar."""

import asyncio
import os
import sys

from hai_avatar.app import build_pipeline
from hai_avatar.config import load_settings
from hai_avatar.logging_config import configure_logging


async def main_async(user_text: str) -> None:
    os.environ["LLM_PROVIDER"] = os.getenv("LLM_PROVIDER", "mock")
    os.environ["TTS_PROVIDER"] = os.getenv("TTS_PROVIDER", "mock")
    os.environ["AVATAR_PROVIDER"] = "prometheus"
    settings = load_settings()
    settings.avatar.provider = "prometheus"
    pipeline = build_pipeline(settings)
    result = await pipeline.process(user_text)
    print("\n[Prometheus smoke result]")
    print(f"reply: {result.reply_text}")
    print(f"command: {result.avatar_command.model_dump(mode='json')}")
    print(f"audio: {result.audio_path}")
    print("open: data/prometheus_avatar/index.html")


if __name__ == "__main__":
    configure_logging()
    text = " ".join(sys.argv[1:]).strip() or "我最近项目压力有点大，不知道怎么开始。"
    asyncio.run(main_async(text))
