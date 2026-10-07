"""Ghostwriter G3: Routen für Interview (lesen, speichern, Fragen vorschlagen) und Lauf mit Quelle Interview."""
from __future__ import annotations

import json

import pytest
from conftest import MOD_PREFIX, OTHER_PROJECT_ID, PROJECT_ID

from backend import ai, interview_ai, run_engine, storage

P = f"{MOD_PREFIX}/projects/{PROJECT_ID}"


@pytest.fixture(autouse=True)
def _free_locks():
    ai._busy.clear()
    ai._rate.clear()
    yield
    ai._busy.clear()


def _book():
    b = storage.create_book(PROJECT_ID, {"title": "Hafen", "kind": "nonfiction", "language": "de"})
    storage.update_book(PROJECT_ID, b["id"], {"ghost": {"model": "claude-sonnet-4-6", "length_words": 300}}, base_version=b["version"])
    ch = storage.get_structure(PROJECT_ID, b["id"])["parts"][0]["chapters"][0]
    return b["id"], ch["id"]


def test_get_put_interview_with_version(client, auth_headers, reader_headers):
    bid, cid = _book()
    url = f"{P}/books/{bid}/interviews/{cid}"
    assert client.get(url, headers=reader_headers).json()["version"] == 0
    q = [{"id": "a" * 32, "question": "Wie kamst du an?", "answer": "Mit dem Zug."}]
    r = client.put(url, json={"base_version": 0, "questions": q}, headers=auth_headers)
    assert r.status_code == 200 and r.json()["version"] == 1
    stale = client.put(url, json={"base_version": 0, "questions": q}, headers=auth_headers)
    assert stale.status_code == 409 and stale.json()["detail"]["code"] == "version_conflict"
    assert stale.json()["detail"]["current"]["questions"][0]["answer"] == "Mit dem Zug."
    bad = client.put(url, json={"base_version": 1, "questions": [{"id": "x", "question": "Q"}]}, headers=auth_headers)
    assert bad.status_code in (400, 404)


def test_reader_and_foreign(client, auth_headers, reader_headers, other_headers):
    bid, cid = _book()
    url = f"{P}/books/{bid}/interviews/{cid}"
    assert client.put(url, json={"base_version": 0, "questions": []}, headers=reader_headers).status_code == 403
    assert client.post(f"{url}/questions", json={"count": 3}, headers=reader_headers).status_code == 403
    assert client.get(url, headers=other_headers).status_code == 404
    assert client.get(f"{MOD_PREFIX}/projects/{OTHER_PROJECT_ID}/books/{bid}/interviews/{cid}", headers=auth_headers).status_code == 404


def test_suggest_questions_route_and_lock(client, auth_headers, monkeypatch):
    bid, cid = _book()

    async def fake(messages, model=None, temperature=0.7, max_tokens=4096):
        return json.dumps({"questions": ["Wie war der erste Tag?", "Wer half dir?"]})
    monkeypatch.setattr(interview_ai, "complete", fake)
    r = client.post(f"{P}/books/{bid}/interviews/{cid}/questions", json={"count": 2}, headers=auth_headers)
    assert r.status_code == 200 and r.json() == {"questions": ["Wie war der erste Tag?", "Wer half dir?"]}
    assert ("testuser", bid) not in ai._busy
    # nichts gespeichert – die Oberfläche übernimmt die Fragen
    assert client.get(f"{P}/books/{bid}/interviews/{cid}", headers=auth_headers).json()["version"] == 0


def test_suggest_questions_error_is_readable_and_frees_lock(client, auth_headers, monkeypatch):
    bid, cid = _book()

    async def boom(messages, model=None, temperature=0.7, max_tokens=4096):
        raise RuntimeError("Schlüssel fehlt")
    monkeypatch.setattr(interview_ai, "complete", boom)
    r = client.post(f"{P}/books/{bid}/interviews/{cid}/questions", json={"count": 2}, headers=auth_headers)
    assert r.status_code == 502 and r.json()["detail"]["code"] == "llm_failed"
    assert ("testuser", bid) not in ai._busy
    bad = client.post(f"{P}/books/{bid}/interviews/{cid}/questions", json={"count": 9}, headers=auth_headers)
    assert bad.status_code == 422


def test_run_estimate_and_start_with_interview_source(client, auth_headers, monkeypatch):
    bid, cid = _book()
    monkeypatch.setattr(run_engine, "start_background", lambda *a, **k: None)
    url = f"{P}/books/{bid}/ghost/run"
    empty = client.get(f"{url}/estimate", params={"scope": "chapter", "chapter_id": cid, "source": "interview"}, headers=auth_headers)
    assert empty.status_code == 400 and empty.json()["detail"]["code"] == "interview_empty"
    client.put(f"{P}/books/{bid}/interviews/{cid}", json={"base_version": 0, "questions": [
        {"id": "a" * 32, "question": "Q?", "answer": "Antwort."}]}, headers=auth_headers)
    e = client.get(f"{url}/estimate", params={"scope": "chapter", "chapter_id": cid, "source": "interview"}, headers=auth_headers)
    assert e.status_code == 200 and e.json()["scenes"] == 1
    r = client.post(url, json={"scope": "chapter", "chapter_id": cid, "source": "interview", "confirm": True}, headers=auth_headers)
    assert r.status_code == 200 and r.json()["options"]["source"] == "interview" and r.json()["options"]["chapter_id"] == cid
    bad = client.post(url, json={"scope": "book", "source": "interview", "confirm": True}, headers=auth_headers)
    assert bad.status_code in (400, 409)
