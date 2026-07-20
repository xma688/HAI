"""Download the official CharacterEval BaichuanCharRM weights.

The model is large (~25 GB). The download is resumable and writes to .tmp by
default so the weights stay out of git.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from huggingface_hub import HfApi, hf_hub_download


DEFAULT_REPO_ID = "morecry/BaichuanCharRM"
DEFAULT_OUTPUT = Path(".tmp") / "BaichuanCharRM"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-id", default=DEFAULT_REPO_ID)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--min-free-gb", type=float, default=35.0)
    args = parser.parse_args()

    total_size = estimate_repo_size(args.repo_id)
    free_gb = shutil.disk_usage(args.output.parent if args.output.parent.exists() else ".").free / 1024**3
    print(f"repo={args.repo_id}")
    print(f"estimated_size_gb={total_size / 1024**3:.2f}")
    print(f"free_space_gb={free_gb:.2f}")
    if free_gb < args.min_free_gb:
        raise SystemExit(f"Not enough free space for CharacterRM download; require at least {args.min_free_gb:.1f}GB.")

    args.output.mkdir(parents=True, exist_ok=True)
    files = repo_files(args.repo_id)
    for filename in files:
        print(f"downloading={filename}", flush=True)
        hf_hub_download(
            repo_id=args.repo_id,
            filename=filename,
            local_dir=str(args.output),
            local_dir_use_symlinks=False,
            resume_download=True,
        )
    print(f"downloaded_to={args.output.resolve()}")


def estimate_repo_size(repo_id: str) -> int:
    info = HfApi().model_info(repo_id, files_metadata=True)
    return sum(sibling.size or 0 for sibling in info.siblings)


def repo_files(repo_id: str) -> list[str]:
    info = HfApi().model_info(repo_id, files_metadata=True)
    return [sibling.rfilename for sibling in info.siblings]


if __name__ == "__main__":
    main()
