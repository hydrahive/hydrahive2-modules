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

        def register_tool(self, tool):
            seen.setdefault("tools", []).append(tool.name)

    backend.register(Ctx())
    assert seen["routers"] == [backend.router]
    assert seen["migrations"] == ["migrations"]
    assert seen["jobs"] == [("recover_stale_runs", runs.recover_stale_runs, 0)]
    assert seen["tools"] == ["storyteller_books", "storyteller_outline", "storyteller_read", "storyteller_propose_text"]


def test_manifest_gives_agents_the_tools_and_capability_covers_them():
    """Master-Agenten bekommen die Werkzeuge automatisch; wer das Modul nicht nutzen darf, dessen Agenten nicht."""
    import json
    from pathlib import Path
    m = json.loads((Path(__file__).resolve().parents[1] / "manifest.json").read_text())
    assert m["default_agent_tools"] is True
    cap = next(c for c in m["capabilities"] if c["id"] == "module.storyteller")
    assert cap["default"] == "admin_only"


def test_core_access_filter_maps_tools_to_storyteller_capability():
    """Mit dem echten Kern-Katalog: alle Storyteller-Werkzeuge hängen an module.storyteller (nur wer das Modul
    nutzen darf, dessen Agenten bekommen sie)."""
    from pathlib import Path

    from backend.agent_tools import TOOLS
    from hydrahive.access.capabilities import Catalog
    from hydrahive.modules.manifest import ModuleManifest
    cat = Catalog.with_core()
    cat.register_module(ModuleManifest.load(Path(__file__).resolve().parents[1] / "manifest.json"))
    for t in TOOLS:
        assert cat.capability_for_tool(t.name, module_id="storyteller") == "module.storyteller"
