"""Gemeinsame Fixtures der Routen-Tests (echter Kern, Modul-Tor module.mailbox, Fake-IMAP)."""
from __future__ import annotations

import pytest
from _fake_imap import FakeIMAP, FakeServer
from fastapi.testclient import TestClient

from conftest import MODULE_DIR, eml

B = "/api/modules/mailbox"
NEW = {"label": "Privat", "address": "alice@example.net", "imap_host": "imap.example.net", "imap_port": 993,
       "imap_tls": "ssl", "smtp_host": "smtp.example.net", "smtp_port": 465, "smtp_tls": "ssl",
       "username": "alice@example.net", "password": "geheim-123"}


@pytest.fixture(scope="module")
def client(setup_test_env):
    from contextlib import asynccontextmanager

    import backend
    from hydrahive.access.capabilities import catalog
    from hydrahive.api import main
    from hydrahive.modules.context import ModuleContext
    from hydrahive.modules.manifest import ModuleManifest
    from hydrahive.modules.registry import REGISTRY, LoadedModule
    manifest = ModuleManifest.load(MODULE_DIR / "manifest.json")
    catalog().register_module(manifest)
    ctx = ModuleContext("mailbox")
    backend.register(ctx)
    saved = dict(REGISTRY)
    REGISTRY.clear()
    REGISTRY["mailbox"] = LoadedModule(name="mailbox", manifest=manifest, path=MODULE_DIR, ctx=ctx, loaded=True)
    try:
        main.mount_module_routers(main.app)
    finally:
        REGISTRY.clear()
        REGISTRY.update(saved)

    @asynccontextmanager
    async def life(app):
        from hydrahive.settings import settings
        settings.ensure_dirs()
        yield
    orig = main.app.router.lifespan_context
    main.app.router.lifespan_context = life
    with TestClient(main.app) as c:
        yield c
    main.app.router.lifespan_context = orig
    catalog().unregister_module("mailbox")


@pytest.fixture(autouse=True)
def rights(monkeypatch):
    """alice + bob dürfen das Modul nutzen, carol nicht."""
    from hydrahive.access import check
    ok = {check.user_id_for("alice"), check.user_id_for("bob")}
    monkeypatch.setattr(check, "_levels", lambda uid: {"module.mailbox": "use"} if uid in ok else {})


@pytest.fixture(autouse=True)
def fake_net(monkeypatch, archive):
    from backend import accounts, sync_job
    srv = FakeServer(user="alice@example.net", password="geheim-123")
    srv.box("Gesendet", special="\\Sent")
    srv.boxes["INBOX"].add(eml("attachments"))
    srv.boxes["INBOX"].add(eml("html_tracking"))
    srv.boxes["Gesendet"].add(eml("plain"))
    monkeypatch.setattr(accounts, "_test_login", lambda acc, pw: {"folders": 2})
    monkeypatch.setattr(sync_job, "_open", lambda acc: FakeIMAP(srv))
    return srv


def _h(client, user):
    r = client.post("/api/auth/login", json={"username": user, "password": "testpass123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def alice(client):
    return _h(client, "alice")


@pytest.fixture
def acc(client, alice):
    r = client.post(f"{B}/accounts", json=NEW, headers=alice)
    assert r.status_code == 201, r.text
    a = r.json()
    assert client.post(f"{B}/accounts/{a['id']}/sync", headers=alice).status_code == 202
    return a



def _mid(client, alice, subject):
    return next(x["id"] for x in client.get(f"{B}/messages", params={"q": f'betreff:"{subject}"'}, headers=alice)
                .json()["items"])

