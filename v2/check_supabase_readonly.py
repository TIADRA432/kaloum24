#!/usr/bin/env python3
"""Inspect connectivity and schema metadata, with no Django setup or migrations."""
from __future__ import annotations

import json
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


if __name__ == "__main__":
    raise SystemExit(main())
