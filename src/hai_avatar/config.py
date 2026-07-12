"""YAML and environment-backed configuration loading."""

from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class AppSettings(BaseModel):
    language: str = "zh-CN"
    max_input_chars: int = 500
    max_reply_chars: int = 500


class LLMSettings(BaseModel):
    provider: str = "mock"
    temperature: float = 0.5
    timeout_seconds: int = 30
    max_retries: int = 1


class TTSSettings(BaseModel):
    provider: str = "mock"
    output_dir: Path = Path("assets/temp")
    voice: str = "zh-CN-XiaoxiaoNeural"
    timeout_seconds: int = 30


class AvatarSettings(BaseModel):
    provider: str = "mock"
    reset_after_speech: bool = True
    default_expression: str = "neutral"


class PlannerSettings(BaseModel):
    max_gestures: int = 2
    enable_cooldown: bool = True


class Settings(BaseModel):
    app: AppSettings = AppSettings()
    llm: LLMSettings = LLMSettings()
    tts: TTSSettings = TTSSettings()
    avatar: AvatarSettings = AvatarSettings()
    planner: PlannerSettings = PlannerSettings()


def _deep_update(base: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key] = _deep_update(base[key], value)
        else:
            base[key] = value
    return base


def load_settings(config_path: Path | None = None) -> Settings:
    """Load settings from YAML and selected environment variable overrides."""

    load_dotenv(PROJECT_ROOT / ".env")
    path = config_path or PROJECT_ROOT / "config" / "default.yaml"
    data: dict[str, Any] = {}
    if path.exists():
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    import os

    env_updates = {
        "llm": {"provider": os.getenv("LLM_PROVIDER", data.get("llm", {}).get("provider", "mock"))},
        "tts": {"provider": os.getenv("TTS_PROVIDER", data.get("tts", {}).get("provider", "mock"))},
        "avatar": {"provider": os.getenv("AVATAR_PROVIDER", data.get("avatar", {}).get("provider", "mock"))},
    }
    settings = Settings.model_validate(_deep_update(data, env_updates))
    settings.tts.output_dir = (PROJECT_ROOT / settings.tts.output_dir).resolve()
    return settings
