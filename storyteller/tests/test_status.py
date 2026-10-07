"""Status: nur für angemeldete Nutzer; register() hängt den Router ein."""
from __future__ import annotations

from conftest import MOD_PREFIX


def test_status_needs_login(client):
    assert client.get(f"{MOD_PREFIX}/status").status_code in (401, 403)


def test_status_reports_draft(client, auth_headers):
    r = client.get(f"{MOD_PREFIX}/status", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == {"stage": "files", "storage": "project", "ai": "llm"}


def test_register_adds_router_migrations_and_recovery_job():
    """Ohne Migration gibt es keine Lauf-Tabelle, ohne Job bleiben Läufe nach einem Neustart „laufend“."""
    import backend
    from backend import runs

    seen = {"routers": [], "migrations": [], "jobs": []}

    class Ctx:
        def register_router(self, router):
            seen["routers"].append(router)

        def register_migrations(self, rel_dir):
            seen["migrations"].append(rel_dir)

        def register_job(self, name, fn, interval_seconds, *, initial_delay_seconds=5.0):
            seen["jobs"].append((name, fn, initial_delay_seconds))

    backend.register(Ctx())
    assert seen["routers"] == [backend.router]
    assert seen["migrations"] == ["migrations"]
    assert seen["jobs"] == [("recover_stale_runs", runs.recover_stale_runs, 0)]
