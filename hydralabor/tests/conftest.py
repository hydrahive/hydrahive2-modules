"""Test-Fixtures für Hydra-Labor (Muster radiostream/tests/conftest.py).

incus wird nie echt aufgerufen: `fake_incus` ersetzt `backend.incus.run` (einziger Weg nach incus) und spielt ein
kleines incus mit Netzen, ACLs, Containern und Schnappschüssen nach.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pytest
from _hh_isolation import (  # noqa: F401 - pytest-Hooks, über conftest registriert
    isolated_root,
    only_own_rows,
    pytest_collection_finish,
    pytest_configure,
    pytest_runtest_call,
    pytest_runtest_setup,
    pytest_unconfigure,
)

MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

TABLES = ("module_hydralabor_state", "module_hydralabor_github", "module_hydralabor_submissions")


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
            "boss": {"password_hash": ph, "role": "admin"},
        }, indent=2))
        from hydrahive.db import init_db
        from hydrahive.modules.migrations import apply_module_migrations
        init_db()                               # Projekte löschen braucht die Kern-Tabellen (smb_mounts …)
        apply_module_migrations("hydralabor", MODULE_DIR / "migrations")
        _declare_capabilities()
        _mount_like_core()
        yield tmp_path


def _mount_like_core() -> None:
    """Router über den echten Kern-Weg einhängen (Muster radiostream/tests/conftest.py)."""
    import backend
    from hydrahive.api import main
    from hydrahive.modules.context import ModuleContext
    from hydrahive.modules.manifest import ModuleManifest
    from hydrahive.modules.registry import REGISTRY, LoadedModule

    ctx = ModuleContext("hydralabor")
    backend.register(ctx)
    saved = dict(REGISTRY)
    REGISTRY.clear()
    REGISTRY["hydralabor"] = LoadedModule(name="hydralabor", manifest=ModuleManifest.load(MODULE_DIR / "manifest.json"),
                                          path=MODULE_DIR, ctx=ctx, loaded=True)
    try:
        main.mount_module_routers(main.app)
    finally:
        REGISTRY.clear()
        REGISTRY.update(saved)


def _declare_capabilities() -> None:
    from hydrahive.access.capabilities import catalog
    from hydrahive.modules.manifest import ModuleManifest
    catalog().register_module(ModuleManifest.load(MODULE_DIR / "manifest.json"))


@pytest.fixture
def db_ready(setup_test_env):
    with only_own_rows(*TABLES):
        yield


@pytest.fixture
def fake_incus(monkeypatch):
    from backend import incus
    from fake_incus import FakeIncus
    fake = FakeIncus()
    monkeypatch.setattr(incus, "run", fake.run)
    monkeypatch.setattr(incus, "available", lambda: True)
    return fake


@pytest.fixture
def client(setup_test_env, db_ready):
    from contextlib import asynccontextmanager

    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from hydrahive.api import main

    @asynccontextmanager
    async def minimal_lifespan(app: FastAPI):
        from hydrahive.settings import settings
        settings.ensure_dirs()
        yield

    original = main.app.router.lifespan_context
    main.app.router.lifespan_context = minimal_lifespan
    with TestClient(main.app) as c:
        yield c
    main.app.router.lifespan_context = original


def _login(client, name: str) -> dict:
    r = client.post("/api/auth/login", json={"username": name, "password": "testpass123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def user_headers(client):
    return _login(client, "testuser")


@pytest.fixture
def admin_headers(client):
    return _login(client, "boss")


@pytest.fixture
def fake_github(monkeypatch):
    from backend import github_api
    from fake_github import FakeGitHub
    gh = FakeGitHub()
    monkeypatch.setattr(github_api, "request", gh.request)
    from backend import github_auth

    async def no_wait(_s):
        return None
    monkeypatch.setattr(github_auth.asyncio, "sleep", no_wait)
    from backend import github_repos
    monkeypatch.setattr(github_repos, "_STEP", 0)
    return gh


@pytest.fixture
def ready(fake_github, db_ready, monkeypatch, tmp_path):
    from backend import github_auth, push, submit, submit_box
    from fake_github import TOKEN
    from hydrahive.credentials import _crypto
    from hydrahive.db.connection import db
    from hydrahive.settings import settings
    with db() as c:
        c.execute("INSERT OR REPLACE INTO module_hydralabor_github (id, token_enc, login, user_id, scopes, connected_at) "
                  "VALUES (1, ?, 'nutzer', 4242, 'public_repo', 'x')", (_crypto.encrypt(TOKEN, settings.data_dir),))
        c.commit()
    box = {"changes": {"files": ["core/src/hydrahive/a.py"], "lines": 12}, "diff": "+++ b/a.py\n+x = 1\n",
           "tests": {"ok": True, "summary": "5241 passed in 270.0s", "passed": 5241, "failed": 0, "failures": []},
           "calls": []}

    async def changes(target):
        box["calls"].append(("changes", target))
        return box["changes"]

    async def commit(target, title, login, uid):
        box["calls"].append(("commit", target, title, login, uid))

    async def diff(target):
        box["calls"].append(("diff", target))
        return box["diff"]

    async def tests(target, files):
        box["calls"].append(("tests", target))
        return box["tests"]

    async def bundle(target, workdir):
        box["calls"].append(("bundle", target))
        p = workdir / "labor.bundle"
        p.write_bytes(b"# v2 git bundle\n")
        return p

    async def push_bundle(bundle, *, fork, target, branch, token, workdir):
        box["calls"].append(("push", fork, target, branch, token == TOKEN))
        bundle.unlink()
    for name, fn in (("changes", changes), ("commit", commit), ("diff", diff), ("run_tests", tests), ("bundle", bundle)):
        monkeypatch.setattr(submit_box, name, fn)
    monkeypatch.setattr(push, "push_bundle", push_bundle)
    monkeypatch.setattr(submit, "_workdir", lambda: tmp_path)
    monkeypatch.setattr(submit, "_stamp", lambda: "20261030-1900")
    monkeypatch.setattr(submit, "_versions", lambda: {"hydrahive": "2.0.0", "hydralabor": "0.2.0"})
    yield box
    github_auth.disconnect()
