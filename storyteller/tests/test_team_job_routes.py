"""T1e: Routen der Team-Knöpfe – Katalog, Schätzung, Start, Liste, Abbruch; Rechte."""
from __future__ import annotations

import pytest
from backend import storage, team, team_job_run, team_jobs
from conftest import MOD_PREFIX, PROJECT_ID

P = f"{MOD_PREFIX}/projects/{PROJECT_ID}"


@pytest.fixture
def helpers(setup_test_env):
    """Die Test-Projekt-Mitglieder bekommen ein Team: je Rolle ein Helfer (Spezialist dieses Projekts)."""
    from hydrahive.agents import config as ac
    from hydrahive.projects import config as pc
    before = pc.get(PROJECT_ID)
    made = [ac.create(agent_type="specialist", name=f"T — {r.name}", llm_model="claude-sonnet-4-6", tools=[],
                      owner="testuser", temperature=0.7, max_tokens=1000, thinking_budget=0, project_id=PROJECT_ID)
            for r in team.HELPERS]
    pc.update(PROJECT_ID, allowed_specialists=[a["id"] for a in made])
    yield {r.key: a for r, a in zip(team.HELPERS, made)}
    pc.update(PROJECT_ID, allowed_specialists=before.get("allowed_specialists") or [])
    for a in made:
        ac.delete(a["id"])


@pytest.fixture
def started(monkeypatch):
    calls: list = []
    monkeypatch.setattr(team_job_run, "start", lambda pid, bid, jid, *, task: calls.append((pid, bid, jid, task)))
    return calls


def _book():
    b = storage.create_book(PROJECT_ID, {"title": "Der Leuchtturm", "kind": "novel", "model": "claude-sonnet-4-6"})
    ch = storage.get_structure(PROJECT_ID, b["id"])["parts"][0]["chapters"][0]
    return b["id"], ch["id"], ch["scenes"][0]


def test_catalog_lists_buttons_with_availability(client, reader_headers, helpers):
    bid, _cid, _sid = _book()
    r = client.get(f"{P}/books/{bid}/team/jobs/catalog", headers=reader_headers)
    assert r.status_code == 200
    rows = r.json()
    assert [x["key"] for x in rows] == ["check_scene", "edit_scene", "critique_chapter", "structure_chapter",
                                        "update_profiles"]
    assert all(x["available"] for x in rows) and rows[0]["scope"] == "scene" and rows[0]["label"]


def test_catalog_marks_missing_helper_unavailable(client, auth_headers):
    bid, _cid, _sid = _book()
    rows = client.get(f"{P}/books/{bid}/team/jobs/catalog", headers=auth_headers).json()
    assert rows and not any(x["available"] for x in rows)


def test_estimate_then_start_then_list(client, auth_headers, helpers, started):
    bid, _cid, sid = _book()
    e = client.post(f"{P}/books/{bid}/team/jobs/estimate", json={"job": "check_scene", "place_id": sid},
                    headers=auth_headers)
    assert e.status_code == 200 and e.json()["model"] == "claude-sonnet-4-6" and e.json()["input_tokens"] > 0
    r = client.post(f"{P}/books/{bid}/team/jobs", json={"job": "check_scene", "place_id": sid}, headers=auth_headers)
    assert r.status_code == 200
    job = r.json()
    assert job["status"] == "queued" and job["agent_id"] == helpers["plausibility"]["id"]
    assert job["user"] == "testuser" and job["estimate_micros"] == e.json()["cost_micros"]
    assert job["place_title"] and job["agent_name"].endswith("Plausibilität")
    (pid, b, jid, task), = started
    assert (pid, b, jid) == (PROJECT_ID, bid, job["id"]) and sid in task and bid in task
    listed = client.get(f"{P}/books/{bid}/team/jobs", headers=auth_headers).json()
    assert [x["id"] for x in listed] == [job["id"]]


def _limit(bid, limit):
    b = storage.get_book(PROJECT_ID, bid)
    storage.update_book(PROJECT_ID, bid, {"ghost": {"limit_tokens": limit}}, base_version=b["version"])


def _fixed(monkeypatch, tin=4000, tout=3000):
    from backend import team_job_estimate
    orig = team_job_estimate.estimate

    def fake(*a, **k):
        return {**orig(*a, **k), "input_tokens": tin, "output_tokens": tout}
    monkeypatch.setattr(team_job_estimate, "estimate", fake)


def test_estimate_reports_total_limit_and_over(client, auth_headers, helpers, started, monkeypatch):
    """A1 (Spec kostengrenze.md §4): Schätzung gesamt + Grenze des Buchs + „über der Grenze“."""
    bid, _cid, sid = _book()
    _limit(bid, 5000)
    _fixed(monkeypatch)
    e = client.post(f"{P}/books/{bid}/team/jobs/estimate", json={"job": "check_scene", "place_id": sid},
                    headers=auth_headers).json()
    assert e["total_tokens"] == 7000 and e["limit_tokens"] == 5000 and e["over_limit"] is True


def test_start_over_limit_needs_confirmation(client, auth_headers, helpers, started, monkeypatch):
    bid, _cid, sid = _book()
    _limit(bid, 5000)
    _fixed(monkeypatch)                              # Ausgabe allein (3000) unter der Grenze, gesamt 7000 darüber
    url = f"{P}/books/{bid}/team/jobs"
    r = client.post(url, json={"job": "check_scene", "place_id": sid}, headers=auth_headers)
    assert r.status_code == 400 and r.json()["detail"]["code"] == "over_limit"
    assert started == [] and team_jobs.list_jobs(PROJECT_ID, bid) == []
    r = client.post(url, json={"job": "check_scene", "place_id": sid, "confirm_over_limit": True}, headers=auth_headers)
    assert r.status_code == 200 and r.json()["limit_tokens"] == 0      # bestätigt → Grenze gilt für diesen Auftrag nicht
    assert len(started) == 1


def test_start_under_limit_stores_the_limit(client, auth_headers, helpers, started, monkeypatch):
    bid, _cid, sid = _book()
    _limit(bid, 8000)
    _fixed(monkeypatch)
    r = client.post(f"{P}/books/{bid}/team/jobs", json={"job": "check_scene", "place_id": sid}, headers=auth_headers)
    assert r.status_code == 200 and r.json()["limit_tokens"] == 8000
    e = client.post(f"{P}/books/{bid}/team/jobs/estimate", json={"job": "edit_scene", "place_id": sid},
                    headers=auth_headers).json()
    assert e["over_limit"] is False


def test_no_limit_is_never_over(client, auth_headers, helpers, started, monkeypatch):
    bid, _cid, sid = _book()
    _fixed(monkeypatch, tin=10_000_000)
    e = client.post(f"{P}/books/{bid}/team/jobs/estimate", json={"job": "check_scene", "place_id": sid},
                    headers=auth_headers).json()
    assert e["limit_tokens"] == 0 and e["over_limit"] is False
    r = client.post(f"{P}/books/{bid}/team/jobs", json={"job": "check_scene", "place_id": sid}, headers=auth_headers)
    assert r.status_code == 200 and r.json()["limit_tokens"] == 0


def test_reader_may_list_but_not_start_or_cancel(client, auth_headers, reader_headers, helpers, started):
    bid, _cid, sid = _book()
    assert client.post(f"{P}/books/{bid}/team/jobs", json={"job": "check_scene", "place_id": sid},
                       headers=reader_headers).status_code == 403
    assert client.post(f"{P}/books/{bid}/team/jobs/estimate", json={"job": "check_scene", "place_id": sid},
                       headers=reader_headers).status_code == 403
    job = client.post(f"{P}/books/{bid}/team/jobs", json={"job": "check_scene", "place_id": sid},
                      headers=auth_headers).json()
    assert client.get(f"{P}/books/{bid}/team/jobs", headers=reader_headers).status_code == 200
    assert client.post(f"{P}/books/{bid}/team/jobs/{job['id']}/cancel", headers=reader_headers).status_code == 403
    assert started and len(started) == 1


def test_foreign_user_gets_404(client, other_headers, helpers, started):
    bid, _cid, sid = _book()
    assert client.get(f"{P}/books/{bid}/team/jobs", headers=other_headers).status_code == 404
    assert client.post(f"{P}/books/{bid}/team/jobs", json={"job": "check_scene", "place_id": sid},
                       headers=other_headers).status_code == 404
    assert not started


def test_bad_inputs(client, auth_headers, helpers, started):
    bid, cid, sid = _book()
    url = f"{P}/books/{bid}/team/jobs"
    assert client.post(url, json={"job": "rm_rf", "place_id": sid}, headers=auth_headers).status_code == 400
    assert client.post(url, json={"job": "check_scene", "place_id": cid}, headers=auth_headers).status_code == 404
    assert client.post(url, json={"job": "critique_chapter", "place_id": sid}, headers=auth_headers).status_code == 404
    assert client.post(f"{P}/books/{'0' * 32}/team/jobs", json={"job": "check_scene", "place_id": sid},
                       headers=auth_headers).status_code == 404
    assert not started


def test_missing_helper_is_409_and_nothing_starts(client, auth_headers, started):
    bid, _cid, sid = _book()
    r = client.post(f"{P}/books/{bid}/team/jobs", json={"job": "check_scene", "place_id": sid}, headers=auth_headers)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "helper_missing"
    assert not started and team_jobs.list_jobs(PROJECT_ID, bid) == []


def test_second_start_of_same_helper_is_409(client, auth_headers, helpers, started):
    bid, _cid, sid = _book()
    body = {"job": "check_scene", "place_id": sid}
    assert client.post(f"{P}/books/{bid}/team/jobs", json=body, headers=auth_headers).status_code == 200
    r = client.post(f"{P}/books/{bid}/team/jobs", json=body, headers=auth_headers)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "job_busy" and len(started) == 1


def test_cancel(client, auth_headers, helpers, started, monkeypatch):
    bid, _cid, sid = _book()
    job = client.post(f"{P}/books/{bid}/team/jobs", json={"job": "check_scene", "place_id": sid},
                      headers=auth_headers).json()
    r = client.post(f"{P}/books/{bid}/team/jobs/{job['id']}/cancel", headers=auth_headers)
    assert r.status_code == 200 and team_jobs.get(PROJECT_ID, bid, job["id"])["cancel_requested"] is True
    team_jobs.finish(PROJECT_ID, bid, job["id"], status="cancelled")
    assert client.post(f"{P}/books/{bid}/team/jobs/{job['id']}/cancel", headers=auth_headers).status_code == 409


def test_cancel_route_stops_a_live_run(helpers, monkeypatch):
    """Ohne Fake-Start: echter Task läuft (Fake-Runner hängt), die Route bricht ihn ab → cancelled."""
    import asyncio

    import httpx
    from hydrahive.api import main
    from hydrahive.runner.events import Done

    async def slow(session_id, user_input, **kw):
        await asyncio.sleep(30)
        yield Done(message_id="m", iterations=1)
    monkeypatch.setattr(team_job_run, "_runner", lambda: slow)
    bid, _cid, sid = _book()

    async def scenario():
        transport = httpx.ASGITransport(app=main.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
            tok = (await c.post("/api/auth/login", json={"username": "testuser", "password": "testpass123"})).json()
            h = {"Authorization": f"Bearer {tok['access_token']}"}
            job = (await c.post(f"{P}/books/{bid}/team/jobs", json={"job": "check_scene", "place_id": sid},
                                headers=h)).json()
            for _ in range(50):
                if team_jobs.get(PROJECT_ID, bid, job["id"])["status"] == "running":
                    break
                await asyncio.sleep(0.02)
            assert job["id"] in team_job_run.live_ids()
            r = await c.post(f"{P}/books/{bid}/team/jobs/{job['id']}/cancel", headers=h)
            assert r.status_code == 200
            for _ in range(50):
                if not team_job_run.live_ids():
                    break
                await asyncio.sleep(0.02)
            # Noch INNERHALB der Schleife prüfen – asyncio.run bricht beim Beenden sonst selbst alle Tasks ab.
            assert team_job_run.live_ids() == set()
            assert team_jobs.get(PROJECT_ID, bid, job["id"])["status"] == "cancelled"
    asyncio.run(scenario())
