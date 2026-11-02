#!/usr/bin/env python3
"""Read Temporary Access status using a scoped PAT; never enable or grant access."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request

from check_supabase_readonly import load_env_file
from config.database import PROJECT_REF

# The API reference uses /jit-access; the guide's /database/jit-access is stale.
ENDPOINT = f"https://api.supabase.com/v1/projects/{PROJECT_REF}/jit-access"


def main() -> int:
    token = os.environ.get("SUPABASE_ACCESS_TOKEN", "").strip()
    if not token:
        print("SUPABASE_ACCESS_TOKEN is missing from the local environment.", file=sys.stderr)
        return 2
    request = urllib.request.Request(ENDPOINT, headers={"Authorization": f"Bearer {token}"}, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            result = json.load(response)
        state = result.get("state")
        if not isinstance(state, str) or state not in {"enabled", "disabled", "unavailable"}:
            print("Temporary access returned an unexpected status; no changes made.", file=sys.stderr)
            return 1
        output = {"project_ref": PROJECT_REF, "temporary_access_state": state}
        if state == "unavailable":
            # Only emit a known, non-secret reason; never log arbitrary API bodies.
            output["unavailable_reason"] = (
                "ssl_enforcement_required"
                if result.get("unavailableReason") == "ssl_enforcement_required" else "unspecified"
            )
        if isinstance(result.get("appliedSuccessfully"), bool):
            output["applied_successfully"] = result["appliedSuccessfully"]
        print(json.dumps(output))
    except urllib.error.HTTPError as error:
        print(f"Temporary access status failed (HTTP {error.code}); check token validity and Project Settings Read permission.", file=sys.stderr)
        return 1
    except (urllib.error.URLError, OSError, ValueError, AttributeError):
        print("Temporary access status could not be read; no changes made.", file=sys.stderr)
        return 1
    return 0


def cli() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, help="Explicit local .env file (never printed).")
    args = parser.parse_args()
    if args.env_file:
        try:
            load_env_file(args.env_file)
        except (OSError, UnicodeError):
            print("Cannot read the selected local environment file.", file=sys.stderr)
            return 2
    return main()


if __name__ == "__main__":
    raise SystemExit(cli())
