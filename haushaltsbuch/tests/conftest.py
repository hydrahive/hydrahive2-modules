from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _hh_isolation import (  # noqa: E402, F401 - pytest-Hooks, über conftest registriert
    TEST_ROOT,
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

import bcrypt  # noqa: E402
import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

MODULE_DIR = Path(__file__).resolve().parents[1]
CORE_SRC = MODULE_DIR.parents[1] / "hydrahive2" / "core" / "src"
for path in (MODULE_DIR, CORE_SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

_ROOT = TEST_ROOT
os.environ.update(
    {
        "HH_SECRET_KEY": "haushaltsbuch-test-secret-key",
        "HH_DISCORD_ENABLED": "0",
        "HH_WA_ENABLED": "0",
        "HH_AGENTLINK_URL": "",
        "HH_PG_MIRROR_DSN": "",
        "HH_HAUSHALTSBUCH_LIDL_ENABLED": "1",
    }
)
(_ROOT / "data" / "agents").mkdir(parents=True, exist_ok=True)
(_ROOT / "config").mkdir(parents=True, exist_ok=True)
_password = bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode("ascii")
(_ROOT / "config" / "users.json").write_text(
    json.dumps(
        {
            "owner": {
                "user_id": "user-owner",
                "password_hash": _password,
                "role": "user",
            },
            "member": {
                "user_id": "user-member",
                "password_hash": _password,
                "role": "user",
            },
            "outsider": {
                "user_id": "user-outsider",
                "password_hash": _password,
                "role": "user",
            },
        }
    )
)

PREFIX = "/api/modules/haushaltsbuch"


@pytest.fixture(scope="session")
def app() -> FastAPI:
    from backend import (
        household_router, import_router, ledger_router, loyalty_router,
        planning_router, router,
    )

    instance = FastAPI()
    for module_router in (
        router, household_router, import_router, ledger_router, loyalty_router,
        planning_router,
    ):
        instance.include_router(module_router, prefix=PREFIX)
    return instance


@pytest.fixture
def client(app: FastAPI):
    """Nach jedem Test nur die Haushaltsbuch-Zeilen entfernen, die er angelegt hat."""
    from hydrahive.db import init_db
    from hydrahive.db.connection import db
    from hydrahive.modules.migrations import apply_module_migrations

    init_db()
    apply_module_migrations("haushaltsbuch", MODULE_DIR / "migrations")
    with db() as conn:
        tables = [
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' "
                "AND name LIKE 'module\\_haushaltsbuch\\_%' ESCAPE '\\' ORDER BY name"
            )
        ]
    with only_own_rows(*tables):
        yield TestClient(app)


def headers(username: str) -> dict[str, str]:
    from hydrahive.api.middleware.auth import create_token

    users = {
        "owner": "user-owner",
        "member": "user-member",
        "outsider": "user-outsider",
    }
    return {
        "Authorization": f"Bearer {create_token(username, 'user', users[username])}"
    }


@pytest.fixture
def owner_headers() -> dict[str, str]:
    return headers("owner")


@pytest.fixture
def member_headers() -> dict[str, str]:
    return headers("member")


@pytest.fixture
def outsider_headers() -> dict[str, str]:
    return headers("outsider")
