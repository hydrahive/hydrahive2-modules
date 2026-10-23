"""Test-Fixtures für Mailbox (Isolation wie alle Module: _hh_isolation zuerst)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _hh_isolation import (  # noqa: E402, F401, I001 - pytest-Hooks; MUSS vor jedem weiteren Import stehen
    isolated_root,
    only_own_files,
    only_own_rows,
    pytest_collection_finish,
    pytest_configure,
    pytest_runtest_call,
    pytest_runtest_setup,
    pytest_unconfigure,
    remove_test_tree,
)

import pytest  # noqa: E402, I001

MODULE_DIR = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

TABLES = ("module_mailbox_accounts", "module_mailbox_sync", "module_mailbox_sendlog", "module_mailbox_settings",
          "module_mailbox_shares", "module_mailbox_audit")


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    with isolated_root() as tmpdir:
        tmp_path = Path(tmpdir)
        os.environ["HH_SECRET_KEY"] = "test-secret-key-for-jwt-signing-at-least-32-bytes"
        os.environ["HH_DISCORD_ENABLED"] = "0"
        os.environ["HH_WA_ENABLED"] = "0"
        os.environ["HH_AGENTLINK_URL"] = ""
        os.environ["HH_PG_MIRROR_DSN"] = ""
        (tmp_path / "data" / "agents").mkdir(parents=True, exist_ok=True)
        (tmp_path / "config").mkdir(parents=True, exist_ok=True)

        import bcrypt
        pw_hash = bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode("ascii")
        (tmp_path / "config" / "users.json").write_text(json.dumps({
            "alice": {"password_hash": pw_hash, "role": "user"},
            "bob": {"password_hash": pw_hash, "role": "user"},
            "carol": {"password_hash": pw_hash, "role": "user"},
            "root": {"password_hash": pw_hash, "role": "admin"},
        }, indent=2))

        from hydrahive.db import init_db
        from hydrahive.modules.migrations import apply_module_migrations
        init_db()
        apply_module_migrations("mailbox", MODULE_DIR / "migrations")
        yield tmp_path


@pytest.fixture(autouse=True)
def clean_rows():
    from hydrahive.db import init_db
    init_db()
    with only_own_rows(*TABLES):
        yield


@pytest.fixture
def archive(tmp_path, monkeypatch):
    """Eigener Archivordner je Test (Index + .eml), damit Tests sich nicht sehen."""
    from backend import paths
    root = tmp_path / "archiv"
    monkeypatch.setattr(paths, "archive_root", lambda: root)
    return root


def eml(name: str) -> bytes:
    return (FIXTURES / f"{name}.eml").read_bytes()
