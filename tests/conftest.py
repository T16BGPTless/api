"""Ensure sibling package `gptless_tests` is importable for any test under `tests/`."""

from __future__ import annotations

import sys
from pathlib import Path

TESTS_DIR = str(Path(__file__).resolve().parent)
if TESTS_DIR not in sys.path:
    sys.path.insert(0, TESTS_DIR)
