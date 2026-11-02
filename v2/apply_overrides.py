#!/usr/bin/env python3
"""Copy the tracked Kaloum24 files into the generated starter, without SQL."""
from __future__ import annotations

from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "site"


def apply_overrides(target: Path = TARGET) -> int:
    target = target.resolve()
    if not (target / "kaloum24_v2" / "settings").is_dir():
        raise RuntimeError("Generate v2/site with bootstrap_v2.py first.")
    sources = [(source, Path("kaloum24_v2/settings") / source.name)
               for source in (ROOT / "config").glob("*.py")]
    sources += [(source, source.relative_to(ROOT / "overrides"))
                for source in (ROOT / "overrides").rglob("*") if source.is_file()]
    for source, relative in sources:
        destination = target / relative
        if source.is_symlink() or not destination.resolve().is_relative_to(target):
            raise RuntimeError("Override paths must remain inside the generated site.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    return len(sources)


if __name__ == "__main__":
    print(f"Applied {apply_overrides()} Kaloum24 files. No database operation performed.")
