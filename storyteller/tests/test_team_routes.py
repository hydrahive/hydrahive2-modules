"""T1c: Route „Buch als eigenes Projekt“ – Rechte (Freigabe storyteller.create_project) + Antwort."""
from __future__ import annotations

from pathlib import Path

import pytest

from conftest import MOD_PREFIX

URL = f"{MOD_PREFIX}/book-projects"
BODY = {"title": "Der Leuchtturm", "kind": "novel", "language": "de", "audience": "", "idea": "", "model": "claude-sonnet-4-6"}
CAP = "storyteller.create_project"


@pytest.fixture(autouse=True)
def _catalog_from_manifest(monkeypatch):
    """Katalog wie im Betrieb (sonst gälte die Freigabe als nicht deklariert = offen)."""
    from hydrahive.access import capabilities
    from hydrahive.modules.manifest import ModuleManifest
    cat = capabilities.Catalog.with_core()
    cat.register_module(ModuleManifest.load(Path(__file__).resolve().parents[1] / "manifest.json"))
    monkeypatch.setattr(capabilities, "CATALOG", cat)


@pytest.fixture
def cleanup():
    from hydrahive.projects import config as pc
    made: list[str] = []
    yield made
    for pid in made:
        pc.delete(pid)


@pytest.fixture
def grant():
    from hydrahive.access import check, grants
    done: list[tuple[str, str]] = []

    def _grant(user: str, cap: str):
        uid = check.user_id_for(user)
        grants.grant(cap, "user", uid, "use", actor_id="test")
        done.append((cap, uid))
    yield _grant
    for cap, uid in done:
        grants.revoke(cap, "user", uid, actor_id="test")


def test_manifest_declares_admin_only_capability():
    import json
    m = json.loads((Path(__file__).resolve().parents[1] / "manifest.json").read_text())
    cap = next(c for c in m["capabilities"] if c["id"] == CAP)
    assert cap["default"] == "admin_only" and cap["label"]


def test_needs_login(client):
    assert client.post(URL, json=BODY).status_code == 401
    assert client.get(f"{URL}/can-create").status_code == 401


def test_user_without_capability_is_refused_and_told_so(client, auth_headers, grant):
    grant("testuser", "module.storyteller")                       # darf Storyteller, aber keine Projekte anlegen
    assert client.get(f"{URL}/can-create", headers=auth_headers).json() == {"can_create": False}
    r = client.post(URL, json=BODY, headers=auth_headers)
    assert r.status_code == 403 and r.json()["detail"]["code"] == "capability_denied"


def test_capability_without_module_access_is_not_enough(client, auth_headers, grant):
    grant("testuser", CAP)
    assert client.get(f"{URL}/can-create", headers=auth_headers).json() == {"can_create": False}
    assert client.post(URL, json=BODY, headers=auth_headers).status_code == 403


def test_user_with_both_grants_creates_project_and_becomes_its_admin(client, auth_headers, grant, cleanup):
    grant("testuser", "module.storyteller")
    grant("testuser", CAP)
    assert client.get(f"{URL}/can-create", headers=auth_headers).json() == {"can_create": True}
    r = client.post(URL, json=BODY, headers=auth_headers)
    assert r.status_code == 200, r.text
    out = r.json()
    cleanup.append(out["project_id"])
    assert out["book"]["title"] == "Der Leuchtturm" and len(out["team"]["helpers"]) == 7
    projects = client.get("/api/projects", headers=auth_headers).json()   # Kern: Nutzer sieht sein neues Projekt
    assert any(p["id"] == out["project_id"] for p in projects)
    book = client.get(f"{MOD_PREFIX}/projects/{out['project_id']}/books/{out['book']['id']}", headers=auth_headers)
    assert book.status_code == 200 and book.json()["can_write"] is True


def test_admin_may_always(client, admin_headers, cleanup):
    assert client.get(f"{URL}/can-create", headers=admin_headers).json() == {"can_create": True}
    r = client.post(URL, json=BODY, headers=admin_headers)
    assert r.status_code == 200
    cleanup.append(r.json()["project_id"])


def test_errors_are_coded(client, admin_headers, monkeypatch):
    from backend.team import setup
    bad = client.post(URL, json={**BODY, "kind": "gedicht"}, headers=admin_headers)
    assert bad.status_code == 400 and bad.json()["detail"]["code"] == "kind_or_language_invalid"
    monkeypatch.setattr(setup, "default_model", lambda: "")
    nomodel = client.post(URL, json={**BODY, "model": ""}, headers=admin_headers)
    assert nomodel.status_code == 409 and nomodel.json()["detail"]["code"] == "no_model"
    too_long = client.post(URL, json={**BODY, "title": "x" * 201}, headers=admin_headers)
    assert too_long.status_code == 422


def test_chat_in_book_project_talks_to_the_author_without_missing_tools(client, admin_headers, cleanup, monkeypatch):
    from backend.agent_tools import TOOLS
    from hydrahive.db import sessions as sessions_db
    from hydrahive.tools import REGISTRY
    for t in TOOLS:
        monkeypatch.setitem(REGISTRY, t.name, t)
    out = client.post(URL, json=BODY, headers=admin_headers).json()
    cleanup.append(out["project_id"])
    base = f"{MOD_PREFIX}/projects/{out['project_id']}/books/{out['book']['id']}/chat"
    info = client.get(base, headers=admin_headers).json()
    assert info["agent"]["id"] == out["team"]["author"] and info["agent"]["name"] == "Der Leuchtturm — Autor"
    assert info["tools_missing"] == []
    started = client.post(base, json={}, headers=admin_headers).json()
    assert sessions_db.get(started["session_id"]).agent_id == out["team"]["author"]
