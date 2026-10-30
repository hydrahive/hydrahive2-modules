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
