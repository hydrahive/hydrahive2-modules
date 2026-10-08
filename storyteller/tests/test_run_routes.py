"""Ghostwriter G2: Routen für Lauf, Gliederung und Vorschläge (Spec §9). LLM gefälscht."""
from __future__ import annotations


import pytest
from _ghost_helpers import fake_llm, make_book
from conftest import MOD_PREFIX, OTHER_PROJECT_ID, PROJECT_ID

from backend import ai, run_engine, runs, storage

P = f"{MOD_PREFIX}/projects/{PROJECT_ID}"


@pytest.fixture(autouse=True)
def _free_locks():
    ai._busy.clear()
    ai._rate.clear()
    yield
    ai._busy.clear()


def _book(n=2, limit=0, length=300, model="claude-sonnet-4-6"):
    return make_book(n, length=length, limit=limit, model=model)


def _fake(monkeypatch, words=300):
    fake_llm(monkeypatch, words=words)


def _run_now(monkeypatch):
    """Echter Start im Hintergrund (wie im Server); merkt sich die gestarteten Läufe."""
    started = []
    real = run_engine.start_background

    def spy(run_id, project_id, book_id, user, lock_key):
        started.append(run_id)
        return real(run_id, project_id, book_id, user, lock_key)
    monkeypatch.setattr(run_engine, "start_background", spy)
    return started


def test_estimate_counts_scenes_and_skips(client, auth_headers):
    bid, cid, sids = _book(3)
    storage.save_scene(PROJECT_ID, bid, sids[1], {"text": "Schon da."}, base_version=2)
    storage.save_scene(PROJECT_ID, bid, sids[2], {"summary": ""}, base_version=2)
    r = client.get(f"{P}/books/{bid}/ghost/run/estimate", params={"scope": "book"}, headers=auth_headers)
    assert r.status_code == 200
    e = r.json()
    assert (e["scenes"], e["skipped_filled"], e["skipped_no_summary"]) == (1, 1, 1)
    assert e["output_tokens"] == int(300 * 1.6) and e["input_tokens"] > 0
    assert e["cost_micros"] and e["model"] == "claude-sonnet-4-6" and e["limit_tokens"] == 0
    r2 = client.get(f"{P}/books/{bid}/ghost/run/estimate", params={"scope": "book", "skip_filled": "false"},
                    headers=auth_headers).json()
    assert r2["scenes"] == 2


def test_estimate_scopes(client, auth_headers):
    bid, cid, sids = _book(3)
    one = client.get(f"{P}/books/{bid}/ghost/run/estimate", params={"scope": "from", "scene_id": sids[1]},
                     headers=auth_headers).json()
    assert one["scenes"] == 2
    ch = client.get(f"{P}/books/{bid}/ghost/run/estimate", params={"scope": "chapter", "chapter_id": cid},
                    headers=auth_headers).json()
    assert ch["scenes"] == 3
    bad = client.get(f"{P}/books/{bid}/ghost/run/estimate", params={"scope": "from"}, headers=auth_headers)
    assert bad.status_code == 400


def test_unknown_model_has_no_cost(client, auth_headers):
    bid, _, _ = _book(1, model="openrouter/irgendwas")
    e = client.get(f"{P}/books/{bid}/ghost/run/estimate", params={"scope": "book"}, headers=auth_headers).json()
    assert e["cost_micros"] is None


def test_start_requires_confirm_and_respects_limit(client, auth_headers, monkeypatch):
    _fake(monkeypatch)
    _run_now(monkeypatch)
    bid, _, _ = _book(2, limit=5000)
    url = f"{P}/books/{bid}/ghost/run"
    r = client.post(url, json={"scope": "book"}, headers=auth_headers)
    assert r.status_code == 400 and r.json()["detail"]["code"] == "confirm_required"
    # 2 Szenen ≈ 1.200 Tokens gesamt (Eingabe + Ausgabe) → unter 5000 → Bestätigung reicht
    r = client.post(url, json={"scope": "book", "confirm": True}, headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.json()["status"] in ("queued", "running", "done")
    # Der Lauf läuft wirklich im Hintergrund durch (Ereignisschleife des Servers).
    import time
    for _ in range(100):
        if client.get(url, headers=auth_headers).json()["status"] == "done":
            break
        time.sleep(0.05)
    got = client.get(url, headers=auth_headers).json()
    assert got["status"] == "done" and [p["state"] for p in got["progress"]] == ["written", "written"]
    assert ("testuser", bid) not in ai._busy


def test_over_limit_needs_extra_confirmation(client, auth_headers, monkeypatch):
    _fake(monkeypatch)
    _run_now(monkeypatch)
    bid, _, _ = _book(3, limit=1000)
    url = f"{P}/books/{bid}/ghost/run"
    r = client.post(url, json={"scope": "book", "confirm": True}, headers=auth_headers)
    assert r.status_code == 400 and r.json()["detail"]["code"] == "over_limit"
    r = client.post(url, json={"scope": "book", "confirm": True, "confirm_over_limit": True}, headers=auth_headers)
    assert r.status_code == 200


def _fixed_estimate(monkeypatch, tin=400, tout=100):
    from backend import _cost
    monkeypatch.setattr(_cost, "scene_estimate", lambda *a, **k: {"sections": 1, "input_tokens": tin, "output_tokens": tout})


def test_over_limit_counts_input_and_output(client, auth_headers, monkeypatch):
    """Spec kostengrenze.md §4: 3 Szenen × (400 + 100) = 1500 gesamt. Ausgabe allein (300) läge unter 1000."""
    _fake(monkeypatch)
    _run_now(monkeypatch)
    _fixed_estimate(monkeypatch)
    bid, _, _ = _book(3, limit=1000)
    e = client.get(f"{P}/books/{bid}/ghost/run/estimate", params={"scope": "book"}, headers=auth_headers).json()
    assert e["total_tokens"] == 1500 and e["limit_tokens"] == 1000
    r = client.post(f"{P}/books/{bid}/ghost/run", json={"scope": "book", "confirm": True}, headers=auth_headers)
    assert r.status_code == 400 and r.json()["detail"]["code"] == "over_limit"


def test_limit_equal_to_estimate_is_not_over(client, auth_headers, monkeypatch):
    _fake(monkeypatch)
    _run_now(monkeypatch)
    _fixed_estimate(monkeypatch)
    bid, _, _ = _book(3, limit=1500)
    r = client.post(f"{P}/books/{bid}/ghost/run", json={"scope": "book", "confirm": True}, headers=auth_headers)
    assert r.status_code == 200, r.text


def test_no_scenes_to_write(client, auth_headers):
    bid, _, sids = _book(1)
    storage.save_scene(PROJECT_ID, bid, sids[0], {"summary": ""}, base_version=2)
    r = client.post(f"{P}/books/{bid}/ghost/run", json={"scope": "book", "confirm": True}, headers=auth_headers)
    assert r.status_code == 400 and r.json()["detail"]["code"] == "nothing_to_write"


def test_second_start_while_active_is_409_and_lock_is_held(client, auth_headers, monkeypatch):
    bid, _, _ = _book(1)
    monkeypatch.setattr(run_engine, "start_background", lambda *a, **k: None)   # Lauf bleibt „queued“
    url = f"{P}/books/{bid}/ghost/run"
    r1 = client.post(url, json={"scope": "book", "confirm": True}, headers=auth_headers)
    assert r1.status_code == 200
    r2 = client.post(url, json={"scope": "book", "confirm": True}, headers=auth_headers)
    assert r2.status_code == 409 and r2.json()["detail"]["code"] == "run_active"
    # Sperre gehört dem Lauf: Szene schreiben (G1) geht nicht
    sid = storage.get_structure(PROJECT_ID, bid)["parts"][0]["chapters"][0]["scenes"][0]
    r3 = client.post(f"{P}/books/{bid}/ghost/scene", json={"scene_id": sid}, headers=auth_headers)
    assert r3.status_code == 409


def test_get_and_cancel_run(client, auth_headers, reader_headers, monkeypatch):
    bid, _, _ = _book(1)
    monkeypatch.setattr(run_engine, "start_background", lambda *a, **k: None)
    run = client.post(f"{P}/books/{bid}/ghost/run", json={"scope": "book", "confirm": True}, headers=auth_headers).json()
    got = client.get(f"{P}/books/{bid}/ghost/run", headers=reader_headers)
    assert got.status_code == 200 and got.json()["id"] == run["id"]
    assert client.post(f"{P}/books/{bid}/ghost/run/cancel", headers=reader_headers).status_code == 403
    r = client.post(f"{P}/books/{bid}/ghost/run/cancel", headers=auth_headers)
    assert r.status_code == 200 and run["id"] in run_engine._cancelled
    run_engine._cancelled.discard(run["id"])


def test_cancel_queued_run_without_task_ends_it_and_frees_lock(client, auth_headers, monkeypatch):
    """Lauf ohne laufenden Task (z. B. noch nicht gestartet) → sofort beendet, Sperre frei."""
    bid, _, _ = _book(1)
    monkeypatch.setattr(run_engine, "start_background", lambda *a, **k: None)
    run = client.post(f"{P}/books/{bid}/ghost/run", json={"scope": "book", "confirm": True}, headers=auth_headers).json()
    client.post(f"{P}/books/{bid}/ghost/run/cancel", headers=auth_headers)
    assert runs.get_run(PROJECT_ID, bid, run["id"])["status"] == "cancelled"
    assert ("testuser", bid) not in ai._busy
    run_engine._cancelled.discard(run["id"])


def test_no_run_yet_is_null(client, auth_headers):
    bid, _, _ = _book(1)
    r = client.get(f"{P}/books/{bid}/ghost/run", headers=auth_headers)
    assert r.status_code == 200 and r.json() is None


def test_reader_and_foreign_project(client, auth_headers, reader_headers, other_headers):
    bid, _, sids = _book(1)
    base = f"{P}/books/{bid}"
    assert client.post(f"{base}/ghost/run", json={"scope": "book", "confirm": True}, headers=reader_headers).status_code == 403
    assert client.post(f"{base}/ghost/outline", json={"chapters": 1, "scenes_per_chapter": 1},
                       headers=reader_headers).status_code == 403
    assert client.get(f"{base}/ghost/run/estimate", params={"scope": "book"}, headers=reader_headers).status_code == 200
    assert client.get(f"{base}/ghost/run", headers=other_headers).status_code == 404
    other = f"{MOD_PREFIX}/projects/{OTHER_PROJECT_ID}/books/{bid}/ghost/run"
    assert client.get(other, headers=auth_headers).status_code == 404
