"""T1f: Route „In eigenes Projekt umziehen“ – Rechte: Anlegen-Freigabe UND Schreibrecht im alten Projekt."""
from __future__ import annotations

from pathlib import Path

import pytest
from backend import storage
from conftest import MOD_PREFIX, PROJECT_ID

CAP = "storyteller.create_project"


@pytest.fixture(autouse=True)
def _catalog_and_tools(monkeypatch):
    from backend.agent_tools import TOOLS
    from hydrahive.access import capabilities
    from hydrahive.modules.manifest import ModuleManifest
    from hydrahive.tools import REGISTRY
    cat = capabilities.Catalog.with_core()
    cat.register_module(ModuleManifest.load(Path(__file__).resolve().parents[1] / "manifest.json"))
    monkeypatch.setattr(capabilities, "CATALOG", cat)
    for t in TOOLS:
        monkeypatch.setitem(REGISTRY, t.name, t)


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


def _url(bid: str) -> str:
    return f"{MOD_PREFIX}/projects/{PROJECT_ID}/books/{bid}/move-to-own-project"


def _book() -> str:
    return storage.create_book(PROJECT_ID, {"title": "Die Verwandlung", "kind": "novel",
                                            "model": "claude-sonnet-4-6"})["id"]


def test_member_with_grants_moves_and_gets_new_project(client, auth_headers, grant, cleanup):
    grant("testuser", "module.storyteller")
    grant("testuser", CAP)
    bid = _book()
    r = client.post(_url(bid), headers=auth_headers)
    assert r.status_code == 200, r.text
    out = r.json()
    cleanup.append(out["project_id"])
    assert out["book_id"] == bid and out["backup"].startswith("trash/moved/")
    opened = client.get(f"{MOD_PREFIX}/projects/{out['project_id']}/books/{bid}", headers=auth_headers)
    assert opened.status_code == 200 and opened.json()["book"]["title"] == "Die Verwandlung"
    assert client.get(f"{MOD_PREFIX}/projects/{PROJECT_ID}/books/{bid}", headers=auth_headers).status_code == 404


def test_without_create_grant_refused_and_book_stays(client, auth_headers, grant):
    grant("testuser", "module.storyteller")
    bid = _book()
    r = client.post(_url(bid), headers=auth_headers)
    assert r.status_code == 403 and r.json()["detail"]["code"] == "capability_denied"
    assert storage.get_book(PROJECT_ID, bid)


def test_reader_of_old_project_refused_even_with_grants(client, reader_headers, grant):
    grant("reader", "module.storyteller")
    grant("reader", CAP)
    bid = _book()
    r = client.post(_url(bid), headers=reader_headers)
    assert r.status_code == 403 and r.json()["detail"]["code"] == "project_read_only"
    assert storage.get_book(PROJECT_ID, bid)


def test_foreign_user_gets_404(client, other_headers, grant):
    grant("other", "module.storyteller")
    grant("other", CAP)
    bid = _book()
    assert client.post(_url(bid), headers=other_headers).status_code == 404
    assert storage.get_book(PROJECT_ID, bid)


def test_errors_are_coded(client, admin_headers, cleanup):
    assert client.post(_url("0" * 32), headers=admin_headers).status_code == 404
    bid = _book()
    first = client.post(_url(bid), headers=admin_headers).json()
    cleanup.append(first["project_id"])
    again = client.post(f"{MOD_PREFIX}/projects/{first['project_id']}/books/{bid}/move-to-own-project",
                        headers=admin_headers)
    assert again.status_code == 409 and again.json()["detail"]["code"] == "already_book_project"


def test_can_move_flag_in_book_list(client, admin_headers, cleanup):
    bid = _book()
    books = client.get(f"{MOD_PREFIX}/projects/{PROJECT_ID}/books", headers=admin_headers).json()
    assert next(b for b in books if b["id"] == bid)["is_book_project"] is False
    out = client.post(_url(bid), headers=admin_headers).json()
    cleanup.append(out["project_id"])
    moved = client.get(f"{MOD_PREFIX}/projects/{out['project_id']}/books", headers=admin_headers).json()
    assert moved[0]["is_book_project"] is True
