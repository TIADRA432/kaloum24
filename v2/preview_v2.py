#!/usr/bin/env python3
"""Open a local, database-free Kaloum24 interface at http://127.0.0.1:8782."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
from wsgiref.simple_server import make_server

from apply_overrides import apply_overrides


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8782)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Choose a local port between 1024 and 65535.")
    apply_overrides()
    sys.path.insert(0, str(Path(__file__).resolve().parent / "site"))
    os.environ["DJANGO_SETTINGS_MODULE"] = "kaloum24_v2.settings.preview"
    from django.core.wsgi import get_wsgi_application
    from django.contrib.staticfiles.handlers import StaticFilesHandler

    application = StaticFilesHandler(get_wsgi_application())
    print(f"Kaloum24 local preview: http://127.0.0.1:{args.port}", flush=True)
    print("Database disabled. Press Ctrl+C to stop.", flush=True)
    with make_server("127.0.0.1", args.port, application) as server:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
