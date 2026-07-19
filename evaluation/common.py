"""Shared helpers for HAI evaluation runners."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from hai_avatar.config import PROJECT_ROOT, load_settings


EVALUATION_ROOT = PROJECT_ROOT / "evaluation"


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def append_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def new_run_dir(prefix: str, output: str | None = None) -> Path:
    if output:
        path = Path(output)
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = EVALUATION_ROOT / "results" / f"{prefix}_{stamp}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def collect_manifest(config_path: Path, run_dir: Path, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    settings = load_settings()
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, text=True).strip()
    except Exception:
        commit = "unknown"
    manifest = {
        "run_dir": str(run_dir),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": commit,
        "python": os.sys.version,
        "config_path": str(config_path),
        "settings": settings.model_dump(mode="json"),
    }
    if extra:
        manifest.update(extra)
    write_json(run_dir / "manifest.json", manifest)
    return manifest
