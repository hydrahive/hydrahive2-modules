"""Baustein 7: „Projekt löschen“ entfernt alles Eigene – und nur das (PLAN-V1.md), dazu Aufräumen nach einem Neustart.

Gegenprobe mit zweitem Projekt: Alles, was zu einem anderen Vibe-Projekt oder zu einem normalen Projekt gehört, bleibt.
`remove` aus Baustein 4 räumt Container, Kern-Projekt, Agent und Datenzeile ab; hier kommen Versionen, Sitzungen und
Waisen dazu.
"""
from __future__ import annotations

import asyncio

import pytest
from backend import container, jobs, network, projects, state, versions, watcher

MODEL = "claude-sonnet-4-6"


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def env(setup_test_env, db_ready, fake_incus, monkeypatch):
    from hydrahive.projects import execution
    monkeypatch.setattr(network, "_host_networks", lambda: set())
    monkeypatch.setattr(network, "_host_addresses", lambda: set())
    monkeypatch.setattr(execution, "_container_exists", lambda name: container.is_vibe_name(name))
    return fake_incus


def _make(name):
    return run(projects.create(admin="boss", name=name, model=MODEL))


def _sessions(agent_id):
    from hydrahive.db import sessions as sdb
    return sdb.list_for_agent(agent_id, limit=50)


def _add_session(agent_id, pid):
    from hydrahive.db import sessions as sdb
    return sdb.create(agent_id=agent_id, user_id="boss", project_id=pid, title="Chat", metadata={"embedded_in": "vibe"})


def _add_version(pid, sha):
    from hydrahive.db.connection import db
    with db() as conn:
        conn.execute("INSERT INTO module_vibe_versions (project_id, commit_id, summary) VALUES (?, ?, 'x')", (pid, sha))
        conn.commit()


def _versions(pid):
    from hydrahive.db.connection import db
    with db() as conn:
        return [r[0] for r in conn.execute("SELECT commit_id FROM module_vibe_versions WHERE project_id = ?", (pid,))]


def test_loeschen_entfernt_sitzungen_des_projekts(env):
    a = _make("A")
    _add_session(a["agent_id"], a["project_id"])
    run(projects.remove(a["project_id"], owner="boss"))
    assert _sessions(a["agent_id"]) == []


def test_loeschen_entfernt_versionszeilen(env):
    a = _make("A")
    _add_version(a["project_id"], "a" * 40)
    run(projects.remove(a["project_id"], owner="boss"))
    assert _versions(a["project_id"]) == []


def test_zweites_projekt_behaelt_sitzungen_und_versionen(env):
    a, b = _make("A"), _make("B")
    _add_session(a["agent_id"], a["project_id"])
    sb = _add_session(b["agent_id"], b["project_id"])
    _add_version(a["project_id"], "a" * 40)
    _add_version(b["project_id"], "b" * 40)
    run(projects.remove(a["project_id"], owner="boss"))
    assert [s.id for s in _sessions(b["agent_id"])] == [sb.id]
    assert _versions(b["project_id"]) == ["b" * 40]
    run(projects.remove(b["project_id"], owner="boss"))


def test_zweites_projekt_behaelt_container_agent_und_zeile(env):
    from hydrahive.agents import config as agent_config
    a, b = _make("A"), _make("B")
    run(projects.remove(a["project_id"], owner="boss"))
    assert container.name_for(b["project_id"]) in env.containers
    assert agent_config.get(b["agent_id"]) and state.get_row(b["project_id"])
    run(projects.remove(b["project_id"], owner="boss"))


def test_fremder_nutzer_loescht_nichts_auch_nicht_versionen(env):
    a = _make("A")
    _add_version(a["project_id"], "a" * 40)
    with pytest.raises(projects.VibeProjectError):
        run(projects.remove(a["project_id"], owner="testuser"))
    assert _versions(a["project_id"]) == ["a" * 40]
    run(projects.remove(a["project_id"], owner="boss"))


def test_normales_projekt_mit_gleicher_id_form_bleibt_unangetastet(env):
    from hydrahive.db import sessions as sdb
    from hydrahive.projects import config as project_config
    normal = project_config.create("Normal", description="x", members=[], llm_model=MODEL, created_by="boss")
    s = sdb.create(agent_id=normal["agent_id"], user_id="boss", project_id=normal["id"], title="Chat")
    a = _make("A")
    run(projects.remove(a["project_id"], owner="boss"))
    assert sdb.get(s.id) is not None and project_config.get(normal["id"])
    project_config.delete(normal["id"])


def test_loeschen_entfernt_den_zustand_des_waechters(env):
    a = _make("A")
    state.set_state(a["project_id"], "ready")
    watcher._state[a["project_id"]] = {"running": False, "sig": "", "pending": False}
    run(projects.remove(a["project_id"], owner="boss"))
    run(watcher.poll())
    assert a["project_id"] not in watcher._state


def test_loeschen_zweimal_ist_kein_fehler(env):
    a = _make("A")
    run(projects.remove(a["project_id"], owner="boss"))
    run(projects.remove(a["project_id"], owner="boss"))


def test_loeschen_waehrend_des_laufs_eines_zuges(env, monkeypatch):
    """Läuft gerade ein Zug, wird er zuerst angehalten, dann gelöscht – sonst schreibt der Lauf in ein totes Projekt."""
    from hydrahive.runner import concurrency
    a = _make("A")
    sess = _add_session(a["agent_id"], a["project_id"])
    stopped: list[str] = []
    holder: dict[str, asyncio.Task] = {}

    def get_task(_sid):
        holder.setdefault("task", asyncio.create_task(asyncio.sleep(3600)))
        return holder["task"]

    def cancel(sid):
        stopped.append(sid)
        holder["task"].cancel()
        return True

    monkeypatch.setattr(concurrency, "get_task", get_task)
    monkeypatch.setattr(concurrency, "is_running", lambda _sid: not holder["task"].done())
    monkeypatch.setattr(concurrency, "cancel", cancel)
    run(projects.remove(a["project_id"], owner="boss"))
    assert stopped == [sess.id] and holder["task"].done()


def test_neustart_vergisst_zustand_der_hoerer_von_gestern(env):
    a = _make("A")
    state.set_state(a["project_id"], "ready")
    watcher._state[a["project_id"]] = {"running": True, "sig": "alt", "pending": True}
    watcher.reset()
    assert watcher._state == {}


def test_waisen_container_ohne_datenzeile_werden_erkannt(env):
    a = _make("A")
    state.delete_row(a["project_id"])                         # Zeile weg, Container bleibt = Waise
    orphans = run(jobs.find_orphans())
    assert container.name_for(a["project_id"]) in orphans["containers"]
    env.containers.pop(container.name_for(a["project_id"]), None)


def test_waisen_werden_nicht_von_selbst_geloescht(env):
    """Aufräumen löscht nie ungefragt: `find_orphans` meldet nur."""
    a = _make("A")
    state.delete_row(a["project_id"])
    run(jobs.find_orphans())
    assert container.name_for(a["project_id"]) in env.containers
    env.containers.pop(container.name_for(a["project_id"]), None)


def test_fremde_container_sind_keine_waisen(env):
    env.containers["hydratest-fremd"] = {"args": [], "running": True, "network": ""}
    env.containers["hh-labor-xyz"] = {"args": [], "running": True, "network": ""}
    orphans = run(jobs.find_orphans())
    assert orphans["containers"] == []


def test_zeilen_ohne_container_werden_erkannt(env):
    a = _make("A")
    env.containers.pop(container.name_for(a["project_id"]))
    orphans = run(jobs.find_orphans())
    assert a["project_id"] in orphans["rows"]
    state.delete_row(a["project_id"])


def test_intakte_projekte_sind_keine_waisen(env):
    a = _make("A")
    orphans = run(jobs.find_orphans())
    assert orphans == {"containers": [], "rows": []}
    run(projects.remove(a["project_id"], owner="boss"))
