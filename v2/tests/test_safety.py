"""Regression tests: no network or database connections are used."""
import contextlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import bootstrap_v2
import check_supabase_readonly as probe
from config.database import database_config, require_supabase_target
from django.core.exceptions import ImproperlyConfigured

URL = "postgresql://postgres:p%40ss@db.qlkeieckyhvpjmyzuwjk.supabase.co:5432/postgres"


class DatabaseSafetyTests(unittest.TestCase):
    def test_tls_readonly_timeout_and_encoded_password(self):
        config = database_config({"DATABASE_URL": URL})
        self.assertEqual(config["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(config["PASSWORD"], "p@ss")
        self.assertEqual(config["OPTIONS"]["sslmode"], "require")
        self.assertIn("default_transaction_read_only=on", config["OPTIONS"]["options"])
        self.assertIn("statement_timeout=10000", config["OPTIONS"]["options"])
        self.assertIsNone(config["OPTIONS"]["prepare_threshold"])
        self.assertTrue(config["DISABLE_SERVER_SIDE_CURSORS"])
        self.assertEqual(config["CONN_MAX_AGE"], 0)
        require_supabase_target(config)

    def test_invalid_urls_and_ssl_downgrades_fail_without_leaking_password(self):
        for url in ("", "sqlite:///tmp/test", "postgresql://postgres:secret@host:bad/db",
                    URL + "?sslmode=disable", URL + "?sslmode=prefer",
                    URL + "?options=-c%20default_transaction_read_only=off",
                    URL + "?sslmode=require&sslmode=disable",
                    "postgresql://postgres:secret@host", URL + "#secret"):
            with self.subTest(url=url):
                with self.assertRaises(ImproperlyConfigured) as error:
                    database_config({"DATABASE_URL": url})
                self.assertNotIn("secret", str(error.exception))
                self.assertNotIn("p%40ss", str(error.exception))

    def test_verified_tls_requires_ca_and_preserves_mode(self):
        for mode in ("verify-ca", "verify-full"):
            with self.subTest(mode=mode):
                with self.assertRaises(ImproperlyConfigured):
                    database_config({"DATABASE_URL": URL, "DATABASE_SSLMODE": mode})
                config = database_config({"DATABASE_URL": URL, "DATABASE_SSLMODE": mode,
                                          "DATABASE_SSLROOTCERT": "/cert/ca.pem"})
                self.assertEqual(config["OPTIONS"]["sslmode"], mode)
                self.assertEqual(config["OPTIONS"]["sslrootcert"], "/cert/ca.pem")
        with self.assertRaises(ImproperlyConfigured):
            database_config({"DATABASE_URL": URL + "?sslmode=verify-full", "DATABASE_SSLMODE": "require"})

    def test_target_guard_accepts_existing_project_only(self):
        for host, user in (("db.other.supabase.co", "postgres"),
                           ("evil.pooler.supabase.com.example.org", "postgres.qlkeieckyhvpjmyzuwjk"),
                           ("aws-0-eu-west-3.pooler.supabase.com", "postgres.other")):
            with self.subTest(host=host), self.assertRaises(ImproperlyConfigured):
                require_supabase_target({"HOST": host, "USER": user})
        require_supabase_target({"HOST": "aws-0-eu-west-3.pooler.supabase.com",
                                 "USER": "postgres.qlkeieckyhvpjmyzuwjk"})


class BootstrapSafetyTests(unittest.TestCase):
    def test_guards_never_spawn_generator(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "site"
            with patch.object(bootstrap_v2, "TARGET", target), patch.object(bootstrap_v2.subprocess, "run") as run:
                for key in ("DATABASE_URL", "PGSERVICE", "PGHOST"):
                    with patch.dict(os.environ, {key: "set"}, clear=True), contextlib.redirect_stderr(io.StringIO()):
                        self.assertEqual(bootstrap_v2.main(), 3)
                target.mkdir()
                with patch.dict(os.environ, {}, clear=True), contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(bootstrap_v2.main(), 2)
                run.assert_not_called()

    def test_generation_uses_current_interpreter_and_copies_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "site"

            def generate(command, **kwargs):
                self.assertTrue(target.is_dir())
                self.assertEqual(command[:4], [sys.executable, "-m", "wagtail.bin.wagtail", "start"])
                self.assertIn(bootstrap_v2.TEMPLATE_COMMIT, command[4])
                (target / "kaloum24_v2" / "settings").mkdir(parents=True)

            with patch.object(bootstrap_v2, "TARGET", target), patch.dict(os.environ, {}, clear=True), \
                 patch.object(bootstrap_v2.subprocess, "run", side_effect=generate), \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(bootstrap_v2.main(), 0)
                self.assertTrue((target / "kaloum24_v2/settings/supabase.py").is_file())

    def test_real_wagtail_entrypoint(self):
        result = subprocess.run([sys.executable, "-m", "wagtail.bin.wagtail", "help", "start"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--template", result.stdout)


class ProbeSafetyTests(unittest.TestCase):
    @patch.object(probe.psycopg, "connect")
    def test_probe_sets_readonly_and_rolls_back(self, connect):
        connection = connect.return_value.__enter__.return_value
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = {"read_only": "on", "ssl": True}
        with patch.dict(os.environ, {"DATABASE_URL": URL}, clear=True), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(probe.main(), 0)
        self.assertTrue(connection.read_only)
        connection.rollback.assert_called_once()
        self.assertIn("default_transaction_read_only=on", connect.call_args.kwargs["options"])
        cursor.execute.assert_called_once_with(probe.QUERY)

    @patch.object(probe.psycopg, "connect")
    def test_probe_rolls_back_after_query_failure(self, connect):
        connection = connect.return_value.__enter__.return_value
        connection.cursor.return_value.__enter__.return_value.execute.side_effect = probe.psycopg.OperationalError("secret")
        output = io.StringIO()
        with patch.dict(os.environ, {"DATABASE_URL": URL}, clear=True), contextlib.redirect_stderr(output):
            self.assertEqual(probe.main(), 1)
        connection.rollback.assert_called_once()
        self.assertNotIn("secret", output.getvalue())

    @patch.object(probe.psycopg, "connect")
    def test_missing_url_never_connects(self, connect):
        with patch.dict(os.environ, {}, clear=True), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(probe.main(), 2)
        connect.assert_not_called()


if __name__ == "__main__":
    unittest.main()
