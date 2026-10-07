"""Ghostwriter G2: Routen für Gliederung aus Idee, abgelegte Vorschläge und Schreibrecht beim Öffnen."""
from __future__ import annotations

import json

import pytest
from _ghost_helpers import make_book
from conftest import MOD_PREFIX, PROJECT_ID

from backend import ai, outline, proposals, storage

P = f"{MOD_PREFIX}/projects/{PROJECT_ID}"


@pytest.fixture(autouse=True)
def _free_locks():
    ai._busy.clear()
    ai._rate.clear()
    yield
    ai._busy.clear()


def _book(n=2, limit=0, length=300, model="claude-sonnet-4-6"):
    return make_book(n, length=length, limit=limit, model=model)


def test_open_book_reports_can_write_and_proposals(client, auth_headers, reader_headers):
    bid, _, sids = _book(1)
    proposals.store(PROJECT_ID, bid, sids[0], "Vorschlag", run_id="r", model="m", base_version=2)
    w = client.get(f"{P}/books/{bid}", headers=auth_headers).json()
    r = client.get(f"{P}/books/{bid}", headers=reader_headers).json()
    assert w["can_write"] is True and r["can_write"] is False
    assert [p["scene_id"] for p in w["proposals"]] == [sids[0]]


def test_proposal_get_accept_discard(client, auth_headers):
    bid, _, sids = _book(2)
    proposals.store(PROJECT_ID, bid, sids[0], "Eins", run_id="r", model="m", base_version=2)
    proposals.store(PROJECT_ID, bid, sids[1], "Zwei", run_id="r", model="m", base_version=2)
    base = f"{P}/books/{bid}/proposals"
    assert client.get(f"{base}/{sids[0]}", headers=auth_headers).json()["text"] == "Eins"
    stale = client.post(f"{base}/{sids[0]}/accept", json={"base_version": 1}, headers=auth_headers)
    assert stale.status_code == 409 and stale.json()["detail"]["code"] == "version_conflict"
    ok = client.post(f"{base}/{sids[0]}/accept", json={"base_version": 2}, headers=auth_headers)
    assert ok.status_code == 200 and ok.json()["text"] == "Eins" and ok.json()["origin"] == "ai_draft"
    assert client.delete(f"{base}/{sids[1]}", headers=auth_headers).status_code == 200
    assert client.get(f"{base}/{sids[1]}", headers=auth_headers).status_code == 404


def test_outline_generate_and_apply(client, auth_headers, monkeypatch):
    b = storage.create_book(PROJECT_ID, {"title": "Neu", "kind": "novel", "language": "de", "idea": "Idee."})
    good = {"chapters": [{"title": "K1", "scenes": [{"title": "a", "summary": "b"}]}], "entities": []}

    async def fake_complete(messages, model=None, temperature=0.7, max_tokens=4096):
        return json.dumps(good)
    monkeypatch.setattr(outline, "complete", fake_complete)
    base = f"{P}/books/{b['id']}/ghost/outline"
    r = client.post(base, json={"chapters": 1, "scenes_per_chapter": 1}, headers=auth_headers)
    assert r.status_code == 200 and r.json()["chapters"][0]["title"] == "K1"
    assert ("testuser", b["id"]) not in ai._busy
    st = storage.get_structure(PROJECT_ID, b["id"])
    a = client.post(f"{base}/apply", json={"outline": r.json(), "base_version": st["version"]}, headers=auth_headers)
    assert a.status_code == 200 and a.json()["structure"]["parts"][0]["chapters"][0]["title"] == "K1"
    stale = client.post(f"{base}/apply", json={"outline": r.json(), "base_version": st["version"]}, headers=auth_headers)
    assert stale.status_code == 409


def test_outline_llm_error_is_readable_and_frees_lock(client, auth_headers, monkeypatch):
    b = storage.create_book(PROJECT_ID, {"title": "Neu", "kind": "novel", "language": "de"})

    async def boom(messages, model=None, temperature=0.7, max_tokens=4096):
        raise RuntimeError("Schlüssel fehlt")
    monkeypatch.setattr(outline, "complete", boom)
    r = client.post(f"{P}/books/{b['id']}/ghost/outline", json={"chapters": 1, "scenes_per_chapter": 1}, headers=auth_headers)
    assert r.status_code == 502 and r.json()["detail"]["code"] == "llm_failed"
    assert ("testuser", b["id"]) not in ai._busy
