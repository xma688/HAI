"""Console entry point for the mock pipeline."""

import asyncio
import json
import sys

from hai_avatar.app import build_mock_pipeline
from hai_avatar.logging_config import configure_logging


async def run_once(user_text: str) -> None:
    pipeline = build_mock_pipeline()
    result = await pipeline.process(user_text)
    print("\n[PipelineResult]")
    print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))


def main() -> None:
    configure_logging()
    user_text = " ".join(sys.argv[1:]).strip() if len(sys.argv) > 1 else input("请输入一句中文文本：").strip()
    asyncio.run(run_once(user_text))


if __name__ == "__main__":
    main()
