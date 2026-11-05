"""Baustein 4: Entfernen, Gegenproben für fremde Projekte, Agent-Skills und Prompt (PLAN-V1.md).

Zweiter Teil zu test_vibe_projects.py (Datei geteilt: höchstens 200 Zeilen je Datei).
"""
from __future__ import annotations

import asyncio

import pytest
from backend import agent_profile, container, network, projects, state

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


def _project(pid):
    from hydrahive.projects import config as project_config
    return project_config.get(pid)


def _agent(aid):
    from hydrahive.agents import config as agent_config
    return agent_config.get(aid)


def test_entfernen_raeumt_alles_ab(env):
    out = run(projects.create(admin="boss", name="Weg", model=MODEL))
    cname = container.name_for(out["project_id"])
    assert cname in env.containers
    run(projects.remove(out["project_id"], owner="boss"))
    assert _project(out["project_id"]) is None and _agent(out["agent_id"]) is None
    assert state.get_row(out["project_id"]) is None and cname not in env.containers
    run(projects.remove(out["project_id"], owner="boss"))                     # zweimal: kein Fehler


def test_entfernen_raeumt_netz_erst_beim_letzten_projekt(env):
    a = run(projects.create(admin="boss", name="A", model=MODEL))
    b = run(projects.create(admin="boss", name="B", model=MODEL))
    run(projects.remove(a["project_id"], owner="boss"))
    assert network.NET in env.networks                                  # B hängt noch daran
    run(projects.remove(b["project_id"], owner="boss"))
    assert network.NET not in env.networks and network.ACL not in env.acls


def test_zweites_projekt_bleibt_beim_entfernen_unveraendert(env):
    a = run(projects.create(admin="boss", name="A", model=MODEL))
    b = run(projects.create(admin="boss", name="B", model=MODEL))
    try:
        run(projects.remove(a["project_id"], owner="boss"))
        assert _project(b["project_id"]) is not None and _agent(b["agent_id"]) is not None
        assert container.name_for(b["project_id"]) in env.containers
        assert [p["project_id"] for p in state.projects_of("boss")] == [b["project_id"]]
    finally:
        run(projects.remove(b["project_id"], owner="boss"))


def test_fremdes_normales_projekt_bleibt_unangetastet(env):
    """Gegenprobe (Spec): Vibe ändert nie ein Projekt, das es nicht selbst angelegt hat."""
    from hydrahive.projects import config as project_config
    from hydrahive.projects import execution
    other = project_config.create("Fremd", members=[], llm_model=MODEL, created_by="boss")
    try:
        before = dict(_project(other["id"]))
        run(projects.remove(other["id"], owner="boss"))                         # kein Vibe-Projekt → nichts passiert
        assert _project(other["id"]) is not None and _agent(other["agent_id"]) is not None
        assert execution.of(_project(other["id"])) == {"mode": "host"}
        out = run(projects.create(admin="boss", name="Eigenes", model=MODEL))
        run(projects.remove(out["project_id"], owner="boss"))
        assert _project(other["id"]) == before and execution.of(_project(other["id"])) == {"mode": "host"}
    finally:
        project_config.delete(other["id"])


def test_set_container_nur_fuer_eigene_projekte(env, monkeypatch):
    from hydrahive.projects import execution
    calls = []
    orig = execution.set_container
    monkeypatch.setattr(execution, "set_container", lambda pid, name, **k: (calls.append((pid, name)), orig(pid, name, **k))[1])
    out = run(projects.create(admin="boss", name="X", model=MODEL))
    try:
        assert calls == [(out["project_id"], container.name_for(out["project_id"]))]
    finally:
        run(projects.remove(out["project_id"], owner="boss"))


def test_fremder_nutzer_kann_nicht_entfernen(env):
    out = run(projects.create(admin="boss", name="Meins", model=MODEL))
    try:
        with pytest.raises(projects.VibeProjectError) as e:
            run(projects.remove(out["project_id"], owner="testuser"))
        assert e.value.code == "vibe_project_not_found"
        assert _project(out["project_id"]) is not None
    finally:
        run(projects.remove(out["project_id"], owner="boss"))


def test_projekt_markierung_noetig_zum_entfernen(env):
    """Hat jemand die Datenzeile für ein fremdes Kern-Projekt angelegt, fasst Vibe es trotzdem nicht an."""
    from hydrahive.db.connection import db
    from hydrahive.projects import config as project_config
    other = project_config.create("Fremd2", members=[], llm_model=MODEL, created_by="boss")
    with db() as conn:
        conn.execute("INSERT INTO module_vibe_projects (project_id, agent_id, container, name, owner) "
                     "VALUES (?,?,?,?,?)", (other["id"], other["agent_id"], "hh-vibe-fake", "Fremd2", "boss"))
        conn.commit()
    try:
        run(projects.remove(other["id"], owner="boss"))
        assert _project(other["id"]) is not None and _agent(other["agent_id"]) is not None
    finally:
        project_config.delete(other["id"])
        with db() as conn:
            conn.execute("DELETE FROM module_vibe_projects WHERE project_id = ?", (other["id"],))
            conn.commit()


# --- Skills und Prompt ------------------------------------------------------------------------------------------

def test_prompt_aus_moduldatei(env):
    out = run(projects.create(admin="boss", name="X", model=MODEL))
    try:
        from hydrahive.agents import config as agent_config
        prompt = agent_config.get_system_prompt(out["agent_id"])
        assert prompt == agent_profile.system_prompt()
        for must in ("VIBE.md", "/work", "Container", "Server", "Vorschau", "einfach"):
            assert must in prompt, must
    finally:
        run(projects.remove(out["project_id"], owner="boss"))


def test_prompt_zeile_pro_antwort_und_keine_geheimnisse():
    p = agent_profile.system_prompt()
    assert "erste Zeile" in p or "erste Zeile jeder Antwort" in p
    assert "Passwörter" in p and "Schlüssel" in p
    assert "kein sudo" in p.lower() or "kein sudo" in p


def test_nur_vibe_skill_sichtbar(env):
    out = run(projects.create(admin="boss", name="X", model=MODEL))
    try:
        a = _agent(out["agent_id"])
        from hydrahive.skills.loader import list_for_agent
        names = {s.name for s in list_for_agent(a["id"], "boss", disabled=a.get("disabled_skills"),
                                                project_id=out["project_id"])}
        assert "vibe-regeln" in names
        for gone in ("hh-review", "git-workflow", "finishing-development-branch", "project-management",
                     "labor-review", "security-audit"):
            assert gone not in names, gone
    finally:
        run(projects.remove(out["project_id"], owner="boss"))


def test_skill_datei_gueltig_und_in_history():
    import json
    import re
    from pathlib import Path
    src = Path(agent_profile.__file__).resolve().parents[1] / "skills"
    text = (src / "vibe-regeln.md").read_text(encoding="utf-8")
    assert text.startswith("---\nname: vibe-regeln\n") and "when_to_use:" in text
    assert re.search(r"^description: .{10,}$", text, re.MULTILINE)
    hist = json.loads((src / "_history.json").read_text(encoding="utf-8"))
    assert hist == {"vibe-regeln.md": []}
    for wort in ("VIBE.md", "Vorschau", "3 Versuche"):
        assert wort in text
