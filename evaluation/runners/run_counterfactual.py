"""Run controlled-profile counterfactual evaluation."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from evaluation.common import append_jsonl, collect_manifest, load_json, load_jsonl, load_yaml, new_run_dir, write_json
from hai_avatar.avatar.mock_controller import MockAvatarController
from hai_avatar.config import PROJECT_ROOT, load_settings
from hai_avatar.llm.mock_provider import MockLLMProvider
from hai_avatar.llm.openai_provider import OpenAIProvider
from hai_avatar.personalization.post_processor import PostProcessor
from hai_avatar.personalization.profile_manager import ProfileManager
from hai_avatar.planner.action_planner import ActionPlanner
from hai_avatar.services.conversation_service import ConversationService
from hai_avatar.services.pipeline_service import PipelineService
from hai_avatar.tts.mock_provider import MockTTSProvider


def build_condition_pipeline(settings, condition: str, provider: str, profile_dir: Path) -> PipelineService:
    llm_provider = MockLLMProvider() if provider == "mock" else OpenAIProvider(settings)
    profile_manager = None if condition == "none" else ProfileManager(profile_dir=profile_dir)
    post_processor = PostProcessor() if condition in ("post", "full") else None
    return PipelineService(
        settings=settings,
        llm_provider=llm_provider,
        tts_provider=MockTTSProvider(),
        avatar_controller=MockAvatarController(),
        action_planner=ActionPlanner(enable_cooldown=False),
        profile_manager=profile_manager,
        post_processor=post_processor,
        conversation_service=ConversationService(),
        use_personalized_prompt=condition in ("prompt", "full"),
        use_post_processor=condition in ("post", "full"),
    )


async def main_async() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="evaluation/configs/eval_mvp.yaml")
    parser.add_argument("--provider", default="mock", choices=["mock", "openai"])
    parser.add_argument("--condition", default="full", choices=["none", "prompt", "post", "full"])
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--output")
    args = parser.parse_args()

    config_path = Path(args.config)
    config = load_yaml(config_path)
    run_dir = new_run_dir(f"counterfactual_{args.condition}", args.output)
    collect_manifest(config_path, run_dir, {"runner": "run_counterfactual", "condition": args.condition})

    settings = load_settings()
    settings.llm.provider = args.provider
    settings.tts.provider = "mock"
    settings.personalization.enabled = args.condition != "none"
    settings.personalization.profile_dir = str(run_dir / "profiles")

    profiles = load_json(PROJECT_ROOT / "evaluation" / "datasets" / "persona_profiles.json")
    scenarios = load_jsonl(PROJECT_ROOT / "evaluation" / "datasets" / "scenarios.jsonl")
    profiles = profiles[: config.get("run", {}).get("max_profiles", len(profiles))]
    scenarios = scenarios[: config.get("run", {}).get("max_scenarios", len(scenarios))]
    if args.limit:
        scenarios = scenarios[: args.limit]

    records = []
    for profile_data in profiles:
        for scenario in scenarios:
            profile_dir = run_dir / "profiles" / args.condition / profile_data["profile_id"] / scenario["scenario_id"]
            pipeline = build_condition_pipeline(settings, args.condition, args.provider, profile_dir)
            if pipeline.profile_manager:
                profile = pipeline.profile_manager.get_or_create(profile_data["profile_id"])
                pipeline.profile_manager.set_self_report(profile, profile_data["big_five"])
                profile.interaction_count = 5
                pipeline.profile_manager._save(profile)
            for turn_index, user_text in enumerate(scenario["turns"]):
                result = await pipeline.process(user_text, user_id=profile_data["profile_id"])
                records.append(
                    {
                        "profile_id": profile_data["profile_id"],
                        "scenario_id": scenario["scenario_id"],
                        "turn_index": turn_index,
                        "condition": args.condition,
                        "user_text": user_text,
                        "result": result.model_dump(mode="json"),
                    }
                )
    append_jsonl(run_dir / "outputs.jsonl", records)
    metrics = {
        "records": len(records),
        "profiles": len(profiles),
        "scenarios": len(scenarios),
        "condition": args.condition,
        "provider": args.provider,
    }
    write_json(run_dir / "metrics.json", metrics)
    print(f"Wrote {len(records)} records to {run_dir}")
    print(metrics)


if __name__ == "__main__":
    asyncio.run(main_async())
