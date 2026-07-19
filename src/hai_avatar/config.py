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
    model: str = "deepseek-v4-flash"
    base_url: str = "https://opencode.ai/zen/go/v1"
    api_key_env: str = "OPENCODE_GO_API_KEY"
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
    prometheus_output_dir: Path = Path("data/prometheus_avatar")
    prometheus_model_url: str = (
        "https://cdn.jsdelivr.net/gh/guansss/pixi-live2d-display@0.4.0/test/assets/haru/"
        "haru_greeter_t03.model3.json"
    )


class PlannerSettings(BaseModel):
    max_gestures: int = 2
    enable_cooldown: bool = True


class PersonalizationSettings(BaseModel):
    enabled: bool = True
    profile_dir: str = "data/profiles"
    update_interval: int = 5
    big_five_learning_rate: float = 0.05
    gesture_affinity_decay: float = 0.95


class Settings(BaseModel):
    app: AppSettings = AppSettings()
    llm: LLMSettings = LLMSettings()
    tts: TTSSettings = TTSSettings()
    avatar: AvatarSettings = AvatarSettings()
    planner: PlannerSettings = PlannerSettings()
    personalization: PersonalizationSettings = PersonalizationSettings()


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

    default_prometheus_model_url = data.get("avatar", {}).get(
        "prometheus_model_url",
        "https://cdn.jsdelivr.net/gh/guansss/pixi-live2d-display@0.4.0/test/assets/haru/"
        "haru_greeter_t03.model3.json",
    )
    env_updates = {
        "llm": {
            "provider": os.getenv("LLM_PROVIDER", data.get("llm", {}).get("provider", "mock")),
            "model": os.getenv("LLM_MODEL", data.get("llm", {}).get("model", "deepseek-v4-flash")),
            "base_url": os.getenv("LLM_BASE_URL", data.get("llm", {}).get("base_url", "https://opencode.ai/zen/go/v1")),
            "api_key_env": os.getenv("LLM_API_KEY_ENV", data.get("llm", {}).get("api_key_env", "OPENCODE_GO_API_KEY")),
        },
        "tts": {"provider": os.getenv("TTS_PROVIDER", data.get("tts", {}).get("provider", "mock"))},
        "avatar": {
            "provider": os.getenv("AVATAR_PROVIDER", data.get("avatar", {}).get("provider", "mock")),
            "prometheus_model_url": os.getenv("PROMETHEUS_MODEL_URL") or default_prometheus_model_url,
        },
    }
    if os.getenv("PERSONALIZATION_ENABLED", "").lower() in ("true", "false"):
        env_updates["personalization"] = {"enabled": os.getenv("PERSONALIZATION_ENABLED").lower() == "true"}
    settings = Settings.model_validate(_deep_update(data, env_updates))
    settings.tts.output_dir = (PROJECT_ROOT / settings.tts.output_dir).resolve()
    return settings
