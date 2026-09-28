"""Isolierte Fixtures für das Telefonie-Modulgrundgerüst."""
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
        "HH_SECRET_KEY": "telephony-test-secret-key-at-least-32-bytes",
        "HH_DISCORD_ENABLED": "0",
        "HH_WA_ENABLED": "0",
        "HH_AGENTLINK_URL": "",
        "HH_PG_MIRROR_DSN": "",
    }
)
(_ROOT / "data" / "agents").mkdir(parents=True, exist_ok=True)
(_ROOT / "config").mkdir(parents=True, exist_ok=True)
(_ROOT / "config" / "users.json").write_text(
    json.dumps(
        {
            "owner": {
                "user_id": "user-owner",
                "password_hash": "not-used",
                "role": "user",
            }
        }
    )
)


@pytest.fixture(scope="session")
def app() -> FastAPI:
    from backend import router

    instance = FastAPI()
    instance.include_router(router, prefix="/api/modules/telephony")
    return instance


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    from hydrahive.api.middleware.auth import create_token

    token = create_token("owner", "user", "user-owner")
    return {"Authorization": f"Bearer {token}"}
