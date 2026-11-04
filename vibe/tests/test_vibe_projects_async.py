"""Baustein 4: create/remove müssen innerhalb des Servers (laufende Ereignisschleife) funktionieren.

Befund 5.11.: Eine synchrone Hülle mit asyncio.run() wirft im Server „cannot be called from a running event loop“.
Die übrigen Tests riefen sie von außen auf und blieben deshalb grün. Hier läuft alles in EINER Schleife wie im Betrieb.
"""
from __future__ import annotations

import asyncio
import inspect

import pytest
from backend import container, network, projects, state

MODEL = "claude-sonnet-4-6"


@pytest.fixture
def env(setup_test_env, db_ready, fake_incus, monkeypatch):
    from hydrahive.projects import execution
    monkeypatch.setattr(network, "_host_networks", lambda: set())
    monkeypatch.setattr(network, "_host_addresses", lambda: set())
    monkeypatch.setattr(container, "_ubuntu_version", lambda: "24.04")
    monkeypatch.setattr(execution, "_container_exists", lambda name: container.is_vibe_name(name))
    return fake_incus


def test_create_und_remove_sind_coroutinen():
    assert inspect.iscoroutinefunction(projects.create)
    assert inspect.iscoroutinefunction(projects.remove)


def test_anlegen_und_entfernen_in_einer_laufenden_schleife(env):
    async def ablauf():
        out = await projects.create(admin="boss", name="Im Server", model=MODEL)
        assert state.get_row(out["project_id"]) is not None
        await projects.remove(out["project_id"], owner="boss")
        return out
    out = asyncio.run(ablauf())
    assert state.get_row(out["project_id"]) is None and not env.containers


def test_zwei_projekte_gleichzeitig_in_einer_schleife(env):
    async def ablauf():
        a, b = await asyncio.gather(projects.create(admin="boss", name="A", model=MODEL),
                                    projects.create(admin="boss", name="B", model=MODEL))
        assert a["project_id"] != b["project_id"]
        assert {r["project_id"] for r in map(state.get_row, (a["project_id"], b["project_id"]))} == \
            {a["project_id"], b["project_id"]}
        await asyncio.gather(projects.remove(a["project_id"], owner="boss"), projects.remove(b["project_id"], owner="boss"))
    asyncio.run(ablauf())
    assert not env.containers and network.NET not in env.networks


def test_fehler_in_der_schleife_raeumt_ab_und_meldet_code(env, monkeypatch):
    from hydrahive.projects import config as project_config
    from hydrahive.projects import execution
    monkeypatch.setattr(execution, "_container_exists", lambda name: False)
    before = {p["id"] for p in project_config.list_all()}

    async def ablauf():
        with pytest.raises(projects.VibeProjectError) as e:
            await projects.create(admin="boss", name="X", model=MODEL)
        return e.value.code
    assert asyncio.run(ablauf()) == "vibe_project_failed"
    assert {p["id"] for p in project_config.list_all()} == before and not env.containers


def test_markiertes_projekt_ohne_datenzeile_wird_nicht_entfernt(env):
    """Mutanten-Fund: Trägt ein Kern-Projekt die Vibe-Markierung, hat Vibe aber keine Zeile dazu, hat Vibe es nicht
    angelegt (Import, Kopie, Handarbeit). Dann darf remove() weder Projekt noch Agent noch Container anfassen."""
    from hydrahive.projects import config as project_config

    other = project_config.create("Importiert", members=[], llm_model=MODEL, created_by="boss",
                                  metadata={"vibe": {"project": True}})
    try:
        asyncio.run(projects.remove(other["id"], owner="boss"))
        assert project_config.get(other["id"]) is not None
        from hydrahive.agents import config as agent_config
        assert agent_config.get(other["agent_id"]) is not None
        assert not any(c[0] == "delete" for c in env.calls)
    finally:
        project_config.delete(other["id"])


def test_fehler_beim_anlegen_hinterlaesst_keine_datenzeile(env, monkeypatch):
    """Mutanten-Fund: Scheitert das Anlegen NACH dem Schreiben der Zeile, muss auch die Zeile wieder weg."""
    from backend import projects as p
    from hydrahive.db.connection import db
    orig = p.state.add_row

    def add_then_fail(**k):
        orig(**k)
        raise RuntimeError("kaputt nach der Zeile")
    monkeypatch.setattr(p.state, "add_row", add_then_fail)
    with pytest.raises(projects.VibeProjectError):
        asyncio.run(projects.create(admin="boss", name="X", model=MODEL))
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM module_vibe_projects").fetchone()[0] == 0
    assert not env.containers


def test_leeres_oder_leerzeichen_modell_ohne_pruefung_des_kerns_abgelehnt(env, monkeypatch):
    """Mutanten-Fund: Der Kern winkt ohne Modell-Liste alles durch (auch Leeres). Vibe darf sich nicht darauf verlassen."""
    from hydrahive.agents import _validation
    from hydrahive.projects import config as project_config
    monkeypatch.setattr(_validation, "validate_model", lambda m: None)
    before = {x["id"] for x in project_config.list_all()}
    for leer in ("", "   ", "\n"):
        with pytest.raises(projects.VibeProjectError) as e:
            asyncio.run(projects.create(admin="boss", name="X", model=leer))
        assert e.value.code == "vibe_model_unavailable"
    assert {x["id"] for x in project_config.list_all()} == before and not env.containers


@pytest.mark.parametrize("kaputt", ["project_delete", "delete_row", "network_cleanup"])
def test_ein_fehler_beim_aufraeumen_stoppt_die_uebrigen_schritte_nicht(env, monkeypatch, kaputt):
    """Echte Probe 5.11.: Scheitert ein Aufräumschritt (hier: Tabelle fehlte), blieben Container und Netz stehen.
    Jeder Schritt muss einzeln abgesichert sein, und der ursprüngliche Fehler bleibt der gemeldete."""
    from backend import projects as p
    from hydrahive.projects import config as project_config
    from hydrahive.projects import execution

    monkeypatch.setattr(execution, "_container_exists", lambda name: False)    # löst den Fehler beim Anlegen aus
    boom = RuntimeError("Aufräumen kaputt")

    def raiser(*a, **k):
        raise boom
    if kaputt == "project_delete":
        monkeypatch.setattr(project_config, "delete", raiser)
    elif kaputt == "delete_row":
        monkeypatch.setattr(p.state, "delete_row", raiser)
    else:
        async def araiser(*a, **k):
            raise boom
        monkeypatch.setattr(p.network, "remove_if_unused", araiser)

    async def ablauf():
        with pytest.raises(projects.VibeProjectError) as e:
            await projects.create(admin="boss", name="X", model=MODEL)
        return e.value.code
    assert asyncio.run(ablauf()) == "vibe_project_failed"                      # der erste Fehler bleibt der gemeldete
    assert not env.containers, "Container blieb nach Aufräum-Fehler stehen"
    if kaputt != "network_cleanup":
        assert network.NET not in env.networks and network.ACL not in env.acls, "Netz blieb stehen"
    # was nicht selbst kaputt war, ist weg
    from hydrahive.db.connection import db
    if kaputt != "delete_row":
        with db() as conn:
            assert conn.execute("SELECT COUNT(*) FROM module_vibe_projects").fetchone()[0] == 0
