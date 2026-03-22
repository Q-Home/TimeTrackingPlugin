#!/usr/bin/env python3
"""Shortcut wrapper for the richer demo seed script."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent
    script_path = project_root / "bin" / "backend" / \
        "scripts" / "seed_demo_via_api.py"

    if not script_path.exists():
        raise FileNotFoundError(f"Seed script not found: {script_path}")

    # 👇 Hier geef je je parameters mee
    sys.argv = [
        str(script_path),
        "--days", "365",
        "--end-date", "2026-03-22",
    ]

    runpy.run_path(str(script_path), run_name="__main__")
