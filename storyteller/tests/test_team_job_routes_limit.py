"""A1: Kostengrenze bei Team-Knöpfen – Schätzung mit Gesamt/Grenze/„über“, Start nur bestätigt, Grenze am Auftrag."""
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
