"""Test-Fixtures für das Recht-Modul (Isolation wie alle Module: _hh_isolation zuerst)."""
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

TABLES = ("module_legal_laws", "module_legal_norms", "module_legal_sync", "module_legal_cases",
          "module_legal_parties", "module_legal_deadlines", "module_legal_notes", "module_legal_proposals")


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    with isolated_root() as tmpdir:
        tmp_path = Path(tmpdir)
        os.environ["HH_SECRET_KEY"] = "test-secret-key-for-jwt-signing"
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
            "root": {"password_hash": pw_hash, "role": "admin"},
        }, indent=2))

        from hydrahive.db import init_db
        from hydrahive.modules.migrations import apply_module_migrations
        init_db()
        apply_module_migrations("legal", MODULE_DIR / "migrations")
        yield tmp_path


def fixture_xml(name: str) -> bytes:
    return (FIXTURES / f"{name}.xml").read_bytes()


@pytest.fixture(autouse=True)
def clean_corpus():
    from hydrahive.db import init_db
    init_db()
    with only_own_rows(*TABLES):
        yield
