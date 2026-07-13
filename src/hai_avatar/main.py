"""Console entry point for the chat avatar pipeline."""

import asyncio
import json
import sys

from hai_avatar.app import build_pipeline
from hai_avatar.logging_config import configure_logging


async def run_once(user_text: str, provider: str = "auto") -> None:
    if provider == "mock":
        from hai_avatar.app import build_mock_pipeline

        pipeline = build_mock_pipeline()
    else:
        pipeline = build_pipeline()
    result = await pipeline.process(user_text)
    print("\n[PipelineResult]")
    print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))


def main() -> None:
    configure_logging()
    args = sys.argv[1:]
    provider = "auto"
    text_parts: list[str] = []
    for arg in args:
        if arg.startswith("--provider="):
            provider = arg.split("=", 1)[1]
        else:
            text_parts.append(arg)
    user_text = " ".join(text_parts).strip() if text_parts else input("请输入一句中文文本：").strip()
    asyncio.run(run_once(user_text, provider=provider))


if __name__ == "__main__":
    main()
