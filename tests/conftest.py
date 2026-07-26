"""Test environment settings for restricted Windows sandboxes."""

from pathlib import Path
import os
import tempfile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_TMP = PROJECT_ROOT / ".tmp" / "pytest-temp"
TEST_TMP.mkdir(parents=True, exist_ok=True)

os.environ.setdefault("TMP", str(TEST_TMP))
os.environ.setdefault("TEMP", str(TEST_TMP))
tempfile.tempdir = str(TEST_TMP)
