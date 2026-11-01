#!/usr/bin/env python3
"""Generate the official Wagtail News starter into v2/site only.

Never touches the Flask app or a production database. Network required.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "site"
TEMPLATE_URL = "https://github.com/wagtail/news-template/archive/refs/heads/main.zip"


def main() -> int:
    if TARGET.exists():
        print("Refusing to overwrite existing v2/site; inspect or remove manually.", file=sys.stderr)
        return 2
    if os.getenv("DATABASE_URL"):
        print("Refusing bootstrap with DATABASE_URL set. Use a clean isolated environment.", file=sys.stderr)
        return 3
    subprocess.run(
        [sys.executable, "-m", "wagtail", "start", f"--template={TEMPLATE_URL}", "kaloum24_v2", str(TARGET)],
        cwd=ROOT,
        check=True,
    )
    print("Generated v2/site. Review generated settings, dependencies and sample credentials before running it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
