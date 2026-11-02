"""PostgreSQL settings for inspection only; importing this never connects."""
from __future__ import annotations

from collections.abc import Mapping
import os
from urllib.parse import parse_qs, urlsplit

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

PROJECT_REF = "qlkeieckyhvpjmyzuwjk"


def enforce_read_only_connection(sender, connection, **kwargs) -> None:
    """Enforce inspection mode after the session pooler opens a backend session."""
    if connection.vendor != "postgresql":
        return
    with connection.cursor() as cursor:
        cursor.execute("SET default_transaction_read_only = on")
        cursor.execute("SHOW default_transaction_read_only")
        enabled = cursor.fetchone()[0] == "on"
    if not enabled:
        connection.close()
        raise ImproperlyConfigured("PostgreSQL inspection session must be read-only.")


def database_config(environ: Mapping[str, str] | None = None) -> dict:
    env = os.environ if environ is None else environ
    auth_mode = env.get("DATABASE_AUTH_MODE", "password")
    if auth_mode not in {"password", "access_token"}:
        raise ImproperlyConfigured("DATABASE_AUTH_MODE must be password or access_token.")
    token = env.get("SUPABASE_ACCESS_TOKEN", "").strip()
    if auth_mode == "access_token" and not token:
        raise ImproperlyConfigured("Temporary access requires SUPABASE_ACCESS_TOKEN in the local environment.")
    url = env.get("DATABASE_URL", "")
    try:
        parts = urlsplit(url)
        query = parse_qs(parts.query, keep_blank_values=True)
        if (
            parts.scheme not in {"postgres", "postgresql"}
            or not parts.hostname
            or not parts.username
            or (auth_mode == "password" and not parts.password)
            or not parts.path.strip("/")
            or parts.fragment
            or set(query) - {"sslmode", "sslrootcert", "options"}
            or any(len(values) != 1 for values in query.values())
            or ("options" in query and (auth_mode != "access_token" or query["options"] not in (["-c jit=true"], ["-c jit=on"])))
        ):
            raise ValueError
        config = dj_database_url.parse(url, conn_max_age=0, conn_health_checks=True)
    except (ValueError, KeyError, TypeError):
        # Parsing exceptions can contain passwords; never propagate them.
        raise ImproperlyConfigured("DATABASE_URL must be a PostgreSQL URL with valid credentials and SSL parameters; only the JIT option is allowed for temporary access.") from None

    if auth_mode == "access_token":
        # Restrict the token's destination before handing it to a driver.
        require_supabase_target(config)
        config["PASSWORD"] = token

    mode = env.get("DATABASE_SSLMODE") or query.get("sslmode", ["require"])[0]
    if mode not in {"require", "verify-ca", "verify-full"}:
        raise ImproperlyConfigured("PostgreSQL SSL must use require, verify-ca or verify-full.")
    if env.get("DATABASE_SSLMODE") and "sslmode" in query and query["sslmode"][0] != mode:
        raise ImproperlyConfigured("Conflicting PostgreSQL SSL modes.")
    rootcert = env.get("DATABASE_SSLROOTCERT") or query.get("sslrootcert", [""])[0]
    if mode in {"verify-ca", "verify-full"} and not rootcert:
        raise ImproperlyConfigured("Certificate verification requires DATABASE_SSLROOTCERT or sslrootcert.")
    options = config.setdefault("OPTIONS", {})
    options.update(
        sslmode=mode,
        connect_timeout=10,
        options="-c default_transaction_read_only=on -c statement_timeout=10000",
        # Also safe for Supabase's transaction pooler (port 6543).
        prepare_threshold=None,
    )
    if auth_mode == "access_token" and config["HOST"].endswith(".pooler.supabase.com"):
        # Supavisor needs this flag to authenticate a personal access token.
        # Supavisor checks for literal true; the old guide's jit=on is not accepted.
        options["options"] += " -c jit=true"
    if rootcert:
        options["sslrootcert"] = rootcert
    config["DISABLE_SERVER_SIDE_CURSORS"] = True
    return config


def require_supabase_target(config: dict) -> None:
    """Reject accidental probes of another database or project."""
    host = config["HOST"]
    if host == f"db.{PROJECT_REF}.supabase.co":
        return
    if host.endswith(".pooler.supabase.com") and config["USER"].endswith(f".{PROJECT_REF}"):
        return
    raise ImproperlyConfigured("Read-only probe must target the existing Kaloum24 Supabase project.")
