"""Run the Gradio app with the same real-API settings as Prometheus smoke runs."""

import os

from hai_avatar.config import load_settings
from hai_avatar.ui.gradio_app import create_app


def _select_available_api_key_env() -> str | None:
    for name in ("OPENCODE_GO_API_KEY", "DEEPSEEK_API_KEY", "OPENAI_API_KEY"):
        if os.getenv(name):
            return name
    return None


def _load_real_api_prometheus_settings():
    settings = load_settings()
    settings.llm.provider = "openai"
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
    return settings


if __name__ == "__main__":
    app = create_app(_load_real_api_prometheus_settings())
    app.launch(server_name="0.0.0.0", server_port=7860)
