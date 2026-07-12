"""Load action planner mappings from YAML."""

from pathlib import Path
from typing import Any

import yaml

from hai_avatar.config import PROJECT_ROOT


def load_action_mapping(path: Path | None = None) -> dict[str, Any]:
    mapping_path = path or PROJECT_ROOT / "config" / "action_mapping.yaml"
    if not mapping_path.exists():
        return {}
    return yaml.safe_load(mapping_path.read_text(encoding="utf-8")) or {}
