"""Test-Fixtures fürs Modul Diagramme (Muster wie studio/tests/conftest.py).

Isolierter Datenordner, zwei Nutzer mit je einem Projekt, Router unter /api/modules/diagramme und das Gerät unter
/api/module-device/diagramme. Archify wird in den meisten Tests durch einen gefälschten Lauf ersetzt; der echte Lauf
steht in test_archify_real.py.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _hh_isolation import (  # noqa: E402, F401 - pytest-Hooks, über conftest registriert
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
from fastapi.testclient import TestClient  # noqa: E402

MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

MOD_PREFIX = "/api/modules/diagramme"
DEV_PREFIX = "/api/module-device/diagramme"
PROJECT_ID = "test-project-diagramme"
OTHER_PROJECT_ID = "other-project-diagramme"


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
        ph = bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode("ascii")
        (tmp_path / "config" / "users.json").write_text(json.dumps({
            "testuser": {"password_hash": ph, "role": "user"},
            "other": {"password_hash": ph, "role": "user"},
            "boss": {"password_hash": ph, "role": "admin"},
        }, indent=2))
        for pid, member in ((PROJECT_ID, "testuser"), (OTHER_PROJECT_ID, "other")):
            pdir = tmp_path / "data" / "projects" / pid
            pdir.mkdir(parents=True, exist_ok=True)
            (pdir / "config.json").write_text(json.dumps({
                "id": pid, "name": pid, "members": [member], "created_by": member,
            }, indent=2))

        from hydrahive.api import main
        from backend.device_routes import device_auth, device_router
        from backend.routes import router
        from fastapi import Depends
        main.app.include_router(router, prefix=MOD_PREFIX)
        main.app.include_router(device_router, prefix=DEV_PREFIX, dependencies=[Depends(device_auth)])
        yield tmp_path


@pytest.fixture
def client(setup_test_env):
    from contextlib import asynccontextmanager

    from fastapi import FastAPI

    from hydrahive.db import init_db
    from hydrahive.modules.migrations import apply_module_migrations
    init_db()
    apply_module_migrations("diagramme", MODULE_DIR / "migrations")

    @asynccontextmanager
    async def minimal_lifespan(app: FastAPI):
        from hydrahive.settings import settings
        settings.ensure_dirs()
        yield

    from hydrahive.api import main
    original = main.app.router.lifespan_context
    main.app.router.lifespan_context = minimal_lifespan
    with TestClient(main.app) as c:
        yield c
    main.app.router.lifespan_context = original


@pytest.fixture
def db_ready(setup_test_env):
    """Tabelle da, nach dem Test nur die eigenen Zeilen weg."""
    from hydrahive.db import init_db
    from hydrahive.modules.migrations import apply_module_migrations
    init_db()
    apply_module_migrations("diagramme", MODULE_DIR / "migrations")
    with only_own_rows("module_diagrams"):
        yield


@pytest.fixture
def store_dir(setup_test_env, db_ready):
    """Ablageordner des Moduls; nach dem Test nur die selbst angelegten Dateien weg."""
    from backend import store
    root = store.root()
    root.mkdir(parents=True, exist_ok=True)
    with only_own_files(root, "**/*"):
        yield root


def _login(client, name: str) -> dict:
    r = client.post("/api/auth/login", json={"username": name, "password": "testpass123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def auth_headers(client):
    return _login(client, "testuser")


@pytest.fixture
def other_headers(client):
    return _login(client, "other")


@pytest.fixture
def admin_headers(client):
    return _login(client, "boss")


@pytest.fixture
def ws(setup_test_env):
    from hydrahive.projects._paths import ensure_workspace
    return ensure_workspace(PROJECT_ID)


HTML_OK = "<!doctype html><html><body><svg><text>Agent fragt</text></svg><script>1</script></body></html>"


@pytest.fixture
def fake_archify(monkeypatch):
    """Ersetzt den Archify-Prozess: merkt sich Aufrufe, schreibt eine HTML-Datei oder meldet Fehler."""
    from backend import runner
    state = {"calls": [], "fail": None}

    def fake_run(argv, *, cwd, env, timeout):
        src = Path(cwd) / argv[argv.index("finalize") + 2]
        state["calls"].append({"argv": list(argv), "cwd": Path(cwd), "env": dict(env), "timeout": timeout,
                               "input": src.read_text() if src.is_file() else None})
        if state["fail"]:
            return 1, json.dumps({"ok": False, "diagnostics": state["fail"]})
        out = Path(cwd) / argv[argv.index("finalize") + 3]
        out.write_text(HTML_OK)
        return 0, json.dumps({"ok": True})

    monkeypatch.setattr(runner, "_run_process", fake_run)
    return state
