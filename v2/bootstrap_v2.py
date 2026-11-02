#!/usr/bin/env python3
"""Generate the official Wagtail News starter into v2/site only.

Never touches the Flask app or a production database. Network required.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

from apply_overrides import apply_overrides

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "site"
TEMPLATE_COMMIT = "3758d56f2c31413bdb1b2aaa96cb7b9e8e150ad9"
TEMPLATE_URL = f"https://github.com/wagtail/news-template/archive/{TEMPLATE_COMMIT}.zip"


def main() -> int:
    if TARGET.exists():
        print("Refusing to overwrite existing v2/site; inspect or remove manually.", file=sys.stderr)
        return 2
    if any(os.getenv(key) for key in ("DATABASE_URL", "PGSERVICE", "PGHOST")):
        print("Refusing bootstrap with DATABASE_URL set. Use a clean isolated environment.", file=sys.stderr)
        return 3
    # Django startproject requires an explicitly supplied destination to exist.
    TARGET.mkdir()
    subprocess.run(
        [sys.executable, "-m", "wagtail.bin.wagtail", "start", f"--template={TEMPLATE_URL}", "kaloum24_v2", str(TARGET)],
        cwd=ROOT,
        check=True,
    )
    apply_overrides(TARGET)
    print("Generated v2/site. Review generated settings, dependencies and sample credentials before running it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
