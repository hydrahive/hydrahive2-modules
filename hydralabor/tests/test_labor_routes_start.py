"""Hydra-Labor: Aufträge über die Schnittstelle wirklich starten (ohne Attrappe für jobs.start)."""
from __future__ import annotations

import pytest
from backend import jobs, state

B = "/api/modules/hydralabor"
MODEL = "claude-sonnet-4-6"


@pytest.fixture
def clean(db_ready):
    state.clear()
    yield
    state.clear()


@pytest.mark.parametrize(("job", "path", "body", "ready"), [
    ("probe", "/probe", {}, True), ("reset", "/reset", {}, True), ("test", "/test", {}, True),
    ("remove", "/remove", {"confirm": "LABOR"}, True), ("create", "/create", {"model": MODEL}, False)])
def test_echter_start_ueber_schnittstelle(client, admin_headers, clean, monkeypatch, job, path, body, ready):
    """Ohne Attrappe für jobs.start: Befund hydratest 30.10. – sync-Route lief im Thread ohne Ereignisschleife,
    create_task scheiterte mit 500 und der Zustand blieb auf „läuft“ hängen."""
    import time

    from hydrahive.agents import _validation
    monkeypatch.setattr(_validation, "_available_models", lambda: {MODEL})
    seen = []

    async def quick(report):
        seen.append(job)
    monkeypatch.setitem(jobs.JOBS, job, quick)
    if ready:
        state.set_step("ready")
    r = client.post(B + path, headers=admin_headers, json=body)
    assert r.status_code == 202
    for _ in range(100):
        if not state.get()["running"]:
            break
        time.sleep(0.02)
    assert seen == [job] and state.get()["running"] == "" and state.get()["error_code"] == ""


def test_start_scheitert_gibt_sperre_frei(clean, monkeypatch):
    """Kann der Auftrag nicht gestartet werden, darf der Zustand nicht auf „läuft“ hängen bleiben."""
    with pytest.raises(RuntimeError):
        jobs.start("probe")                                            # außerhalb einer Ereignisschleife
    assert state.get()["running"] == ""


def test_labor_chat_sitzung_einmal_angelegt(client, admin_headers, clean, monkeypatch):
    """„Zum Labor-Chat“: Sitzung mit dem Labor-Agenten im Labor-Projekt, beim zweiten Mal dieselbe."""
    from backend import lab_project
    from hydrahive.db import sessions as sessions_db
    from hydrahive.projects import execution
    monkeypatch.setattr(execution, "_container_exists", lambda name: True)
    made = lab_project.create(admin="boss", model=MODEL)
    try:
        state.mark_made("project", **made)
        state.set_step("ready")
        r1 = client.post(B + "/chat", headers=admin_headers, json={})
        assert r1.status_code == 200
        d = r1.json()
        assert d["url"] == f"/werkstatt/{d['session_id']}"
        s = sessions_db.get(d["session_id"])
        assert s.agent_id == made["agent_id"] and s.project_id == made["project_id"] and s.user_id == "boss"
        assert client.post(B + "/chat", headers=admin_headers, json={}).json()["session_id"] == d["session_id"]
    finally:
        lab_project.remove(made)


def test_labor_chat_nur_wenn_fertig(client, admin_headers, clean):
    state.mark_made("project", project_id="p1", agent_id="a1")      # Teile da, aber nicht fertig
    r = client.post(B + "/chat", headers=admin_headers, json={})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "labor_not_ready"


def test_labor_chat_fertig_ohne_projekt(client, admin_headers, clean):
    state.set_step("ready")
    r = client.post(B + "/chat", headers=admin_headers, json={})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "labor_not_ready"


def test_labor_chat_nimmt_keine_fremde_sitzung(client, admin_headers, clean, monkeypatch):
    """Andere Sitzung mit demselben Agenten in einem anderen Projekt / anderem Agenten im Labor-Projekt zählt nicht."""
    from backend import lab_project
    from hydrahive.db import sessions as sessions_db
    from hydrahive.projects import execution
    monkeypatch.setattr(execution, "_container_exists", lambda name: True)
    made = lab_project.create(admin="boss", model=MODEL)
    other = lab_project.create(admin="boss", model=MODEL)
    try:
        state.mark_made("project", **made)
        state.set_step("ready")
        a = sessions_db.create(agent_id=made["agent_id"], user_id="boss", project_id=other["project_id"], title="x")
        b = sessions_db.create(agent_id=other["agent_id"], user_id="boss", project_id=made["project_id"], title="y")
        sid = client.post(B + "/chat", headers=admin_headers, json={}).json()["session_id"]
        assert sid not in (a.id, b.id)
    finally:
        lab_project.remove(made)
        lab_project.remove(other)


def test_labor_chat_nur_admins(client, user_headers, clean):
    assert client.post(B + "/chat", headers=user_headers, json={}).status_code == 403
