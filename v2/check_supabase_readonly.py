#!/usr/bin/env python3
"""Inspect connectivity and schema metadata, with no Django setup or migrations."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from django.core.exceptions import ImproperlyConfigured
import psycopg
from psycopg.rows import dict_row

from config.database import database_config, require_supabase_target

QUERY = """
SELECT current_database() AS database,
       current_setting('transaction_read_only') AS read_only,
       current_setting('server_version') AS postgres_version,
       (SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid()) AS ssl,
       (SELECT version FROM pg_stat_ssl WHERE pid = pg_backend_pid()) AS tls_version,
       (SELECT count(*) FROM information_schema.tables
        WHERE table_schema = 'public') AS public_table_count,
       (SELECT count(*) FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name LIKE 'wagtail%') AS wagtail_table_count,
       to_regclass('public.django_migrations') IS NOT NULL AS django_migrations_present
"""


def load_env_file(path: Path) -> None:
    """Load explicitly selected local connection fields, without logging values."""
    allowed = {"DATABASE_URL", "DATABASE_SSLMODE", "DATABASE_SSLROOTCERT",
               "DATABASE_AUTH_MODE", "SUPABASE_ACCESS_TOKEN"}
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if key in allowed:
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1]
            os.environ[key] = value


def main() -> int:
    try:
        config = database_config()
        require_supabase_target(config)
        with psycopg.connect(
            dbname=config["NAME"], user=config["USER"], password=config["PASSWORD"],
            host=config["HOST"], port=config["PORT"] or 5432,
            row_factory=dict_row, **config["OPTIONS"],
        ) as connection:
            connection.read_only = True
            try:
                with connection.cursor() as cursor:
                    cursor.execute(QUERY)
                    result = cursor.fetchone()
                    if result["read_only"] != "on" or result["ssl"] is not True:
                        raise RuntimeError("Read-only or TLS verification failed.")
                    print(json.dumps(result, sort_keys=True))
            finally:
                connection.rollback()
    except ImproperlyConfigured as error:
        print(str(error), file=sys.stderr)
        return 2
    except (psycopg.Error, RuntimeError):
        # libpq messages may include connection details: do not log credentials.
        print("Read-only probe failed; verify connection, permissions and TLS settings.", file=sys.stderr)
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
