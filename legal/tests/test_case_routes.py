"""Routen /api/modules/legal/cases… und /deadline/calc (Plan L2 Schritt 4). Kern-Tor (module.legal + Vault-PIN)
wird live geprüft; hier hängt der Router direkt an der App wie in test_routes_tools.py."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

PREFIX = "/api/modules/legal"
CASE = {"title": "Mietsache Hitze", "area": "Mietrecht", "state": "NW", "facts": "Seit Juni zu heiß."}


@pytest.fixture(scope="module")
def client(setup_test_env):
    from contextlib import asynccontextmanager

    from backend.routes import router
    from fastapi import FastAPI
    from hydrahive.api import main
    if not any(getattr(r, "path", "").startswith(PREFIX) for r in main.app.routes):
        main.app.include_router(router, prefix=PREFIX)

    @asynccontextmanager
    async def minimal_lifespan(app: FastAPI):
        from hydrahive.settings import settings
        settings.ensure_dirs()
        yield

    orig = main.app.router.lifespan_context
    main.app.router.lifespan_context = minimal_lifespan
    with TestClient(main.app) as c:
        yield c
    main.app.router.lifespan_context = orig


@pytest.fixture(autouse=True)
def _caps(monkeypatch):
    """Katalog aus dem eigenen Manifest (sonst gälte legal.create_case als offen); alice hat die Freigabe."""
    from pathlib import Path

    from hydrahive.access import capabilities, check
    from hydrahive.modules.manifest import ModuleManifest
    cat = capabilities.Catalog.with_core()
    cat.register_module(ModuleManifest.load(Path(__file__).resolve().parents[1] / "manifest.json"))
    monkeypatch.setattr(capabilities, "CATALOG", cat)
    alice_id = check.user_id_for("alice")
    assert alice_id
    monkeypatch.setattr(check, "_levels", lambda uid: {"legal.create_case": "use", "module.legal": "use"}
                        if uid == alice_id else {"module.legal": "use"})
    from backend.tools import TOOLS
    from hydrahive.tools import REGISTRY
    for t in TOOLS:
        monkeypatch.setitem(REGISTRY, t.name, t)


@pytest.fixture
def made():
    from hydrahive.projects import config as pc
    ids: list[str] = []
    yield ids
    for pid in ids:
        pc.delete(pid)


def _login(client, user):
    r = client.post("/api/auth/login", json={"username": user, "password": "testpass123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _create(client, made, user="alice", **extra):
    r = client.post(f"{PREFIX}/cases", json={**CASE, "model": "claude-sonnet-4-6", **extra},
                    headers=_login(client, user))
    if r.status_code == 201:
        made.append(r.json()["project_id"])
    return r


def test_create_needs_capability(client, made):
    assert _create(client, made, user="bob").status_code == 403
    r = _create(client, made)
    assert r.status_code == 201 and r.json()["case"]["title"] == "Mietsache Hitze"


def test_invalid_case_is_400_with_code(client, made):
    r = _create(client, made, state="XX")
    assert r.status_code == 400 and r.json()["detail"]["code"] == "legal_state_invalid"


def test_list_get_patch_and_member_rules(client, made):
    from hydrahive.projects import config as pc
    pid = _create(client, made).json()["project_id"]
    a, b = _login(client, "alice"), _login(client, "bob")
    assert [c["project_id"] for c in client.get(f"{PREFIX}/cases", headers=a).json()["cases"]] == [pid]
    assert client.get(f"{PREFIX}/cases", headers=b).json()["cases"] == []
    assert client.get(f"{PREFIX}/cases/{pid}", headers=b).status_code == 404
    pc.update(pid, members=[{"username": "bob", "role": "read"}])
    snap = client.get(f"{PREFIX}/cases/{pid}", headers=b).json()
    assert snap["case"]["title"] == "Mietsache Hitze" and snap["role"] == "read"
    assert client.patch(f"{PREFIX}/cases/{pid}", json={"status": "waiting"}, headers=b).status_code == 403
    assert client.patch(f"{PREFIX}/cases/{pid}", json={"status": "waiting"}, headers=a).json()["status"] == "waiting"


def test_parties_deadlines_notes(client, made):
    pid = _create(client, made).json()["project_id"]
    a = _login(client, "alice")
    p = client.post(f"{PREFIX}/cases/{pid}/parties", json={"role": "opponent", "name": "Vermieter"}, headers=a)
    assert p.status_code == 201
    d = client.post(f"{PREFIX}/cases/{pid}/deadlines", json={"label": "Antwort", "event_date": "2027-05-26",
                                                             "kind": "days", "amount": 1}, headers=a)
    assert d.status_code == 201 and d.json()["due_date"] == "2027-05-28"            # Fronleichnam NW
    did = d.json()["id"]
    assert client.patch(f"{PREFIX}/cases/{pid}/deadlines/{did}", json={"status": "done"},
                        headers=a).status_code == 200
    n = client.post(f"{PREFIX}/cases/{pid}/notes", json={"title": "T", "body": "B"}, headers=a)
    assert n.status_code == 201 and n.json()["author"] == "user" and n.json()["author_name"] == "alice"
    snap = client.get(f"{PREFIX}/cases/{pid}", headers=a).json()
    assert len(snap["parties"]) == 1 and snap["deadlines"][0]["status"] == "done" and len(snap["notes"]) == 1
    assert client.delete(f"{PREFIX}/cases/{pid}/parties/{p.json()['id']}", headers=a).status_code == 204
    assert client.delete(f"{PREFIX}/cases/{pid}/deadlines/999999", headers=a).status_code == 404


def test_ids_of_other_case_are_404(client, made):
    a = _login(client, "alice")
    one = _create(client, made).json()["project_id"]
    two = _create(client, made, title="Zweiter").json()["project_id"]
    p = client.post(f"{PREFIX}/cases/{two}/parties", json={"role": "lawyer", "name": "X"}, headers=a).json()
    assert client.delete(f"{PREFIX}/cases/{one}/parties/{p['id']}", headers=a).status_code == 404


def test_proposals_accept_and_reject(client, made):
    from backend import casefile
    pid = _create(client, made).json()["project_id"]
    a = _login(client, "alice")
    pr = casefile.propose(pid, "party", {"role": "lawyer", "name": "RAin Schmidt"}, author_name="Agent")
    pr2 = casefile.propose(pid, "fact", {"text": "X"}, author_name="Agent")
    assert [x["id"] for x in client.get(f"{PREFIX}/cases/{pid}/proposals", headers=a).json()["proposals"]] == [
        pr["id"], pr2["id"]]
    assert client.post(f"{PREFIX}/cases/{pid}/proposals/{pr['id']}/accept", headers=a).status_code == 200
    assert client.post(f"{PREFIX}/cases/{pid}/proposals/{pr['id']}/accept", headers=a).status_code == 409
    assert client.post(f"{PREFIX}/cases/{pid}/proposals/{pr2['id']}/reject", headers=a).status_code == 200
    assert [x["name"] for x in casefile.list_parties(pid)] == ["RAin Schmidt"]


def test_read_member_cannot_decide(client, made):
    from backend import casefile
    from hydrahive.projects import config as pc
    pid = _create(client, made).json()["project_id"]
    pc.update(pid, members=[{"username": "bob", "role": "read"}])
    pr = casefile.propose(pid, "fact", {"text": "X"}, author_name="Agent")
    b = _login(client, "bob")
    assert client.post(f"{PREFIX}/cases/{pid}/proposals/{pr['id']}/accept", headers=b).status_code == 403
    assert client.post(f"{PREFIX}/cases/{pid}/parties", json={"role": "me", "name": "Bob"},
                       headers=b).status_code == 403


def test_deadline_calc_without_case(client):
    h = _login(client, "bob")
    r = client.post(f"{PREFIX}/deadline/calc", json={"event_date": "2027-05-26", "kind": "days", "amount": 1,
                                                     "state": "NW"}, headers=h)
    assert r.status_code == 200 and r.json()["due_date"] == "2027-05-28" and r.json()["steps"]
    bad = client.post(f"{PREFIX}/deadline/calc", json={"event_date": "x", "kind": "days", "amount": 1, "state": "NW"},
                      headers=h)
    assert bad.status_code == 400 and bad.json()["detail"]["code"] == "legal_event_date_invalid"
    assert client.get(f"{PREFIX}/states", headers=h).json()["states"]["NW"] == "Nordrhein-Westfalen"


def test_chat_session_with_case_agent_is_reused(client, made):
    from hydrahive.db import sessions as sessions_db
    from hydrahive.projects import config as pc
    pid = _create(client, made).json()["project_id"]
    a = _login(client, "alice")
    r = client.post(f"{PREFIX}/cases/{pid}/chat", headers=a)
    assert r.status_code == 200
    out = r.json()
    s = sessions_db.get(out["session_id"])
    assert s.project_id == pid and s.agent_id == pc.get(pid)["agent_id"] and s.user_id == "alice"
    assert out["url"] == f"/werkstatt/{out['session_id']}" and "Mietsache Hitze" in s.title
    assert client.post(f"{PREFIX}/cases/{pid}/chat", headers=a).json()["session_id"] == out["session_id"]
    pc.update(pid, members=[{"username": "bob", "role": "read"}])
    assert client.post(f"{PREFIX}/cases/{pid}/chat", headers=_login(client, "bob")).status_code == 403
