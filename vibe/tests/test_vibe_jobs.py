"""Baustein 6: Auftrag „Projekt anlegen und einrichten“ mit sichtbarem Fortschritt (PLAN-V1.md).

Zustände eines Projekts: new → setting_up → ready, bei Fehler failed (mit Code und Schritt). Die Oberfläche liest den
Fortschritt über /state. Nur ein Auftrag je Projekt, und nach einem Neustart gilt ein halber Auftrag als unterbrochen.
"""
from __future__ import annotations

import asyncio

import pytest
from backend import container, jobs, network, projects, provision, state

MODEL = "claude-sonnet-4-6"


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def env(setup_test_env, db_ready, fake_incus, monkeypatch):
    from hydrahive.projects import execution
    monkeypatch.setattr(network, "_host_networks", lambda: set())
    monkeypatch.setattr(network, "_host_addresses", lambda: set())
    monkeypatch.setattr(execution, "_container_exists", lambda name: container.is_vibe_name(name))

    async def fake_setup(pid, report, *, start_at=""):
        for s in provision.STEPS:
            report(s.key)
    monkeypatch.setattr(provision, "setup", fake_setup)
    jobs.reset()
    return fake_incus


def _row(pid):
    return state.get_row(pid)


def test_anlegen_und_einrichten_endet_ready(env):
    out = run(jobs.create_and_setup(admin="boss", name="App", model=MODEL))
    assert _row(out["project_id"])["state"] == "ready"
    run(projects.remove(out["project_id"], owner="boss"))


def test_fortschritt_wird_je_schritt_gemeldet(env, monkeypatch):
    seen: list[str] = []
    orig = state.set_progress

    def spy(pid, step):
        seen.append(step)
        orig(pid, step)
    monkeypatch.setattr(state, "set_progress", spy)
    out = run(jobs.create_and_setup(admin="boss", name="App", model=MODEL))
    assert seen == [s.key for s in provision.STEPS]
    run(projects.remove(out["project_id"], owner="boss"))


def test_zwischenzustand_ist_setting_up(env, monkeypatch):
    states: list[str] = []

    async def spy_setup(pid, report, *, start_at=""):
        states.append(_row(pid)["state"])
        report("user")
        states.append(_row(pid)["progress"])
    monkeypatch.setattr(provision, "setup", spy_setup)
    out = run(jobs.create_and_setup(admin="boss", name="App", model=MODEL))
    assert states == ["setting_up", "user"]
    run(projects.remove(out["project_id"], owner="boss"))


def test_fehler_in_der_einrichtung_failed_mit_schritt_und_code(env, monkeypatch):
    async def kaputt(pid, report, *, start_at=""):
        report("user")
        report("packages")
        raise provision.SetupError("vibe_setup_failed", "packages")
    monkeypatch.setattr(provision, "setup", kaputt)
    with pytest.raises(jobs.JobError) as e:
        run(jobs.create_and_setup(admin="boss", name="App", model=MODEL))
    assert e.value.code == "vibe_setup_failed" and e.value.step == "packages"
    rows = state.projects_of("boss")
    assert len(rows) == 1 and rows[0]["state"] == "failed"
    assert rows[0]["error_code"] == "vibe_setup_failed" and rows[0]["error_step"] == "packages"


def test_failed_projekt_bleibt_zum_wiederholen_und_zum_loeschen(env, monkeypatch):
    async def kaputt(pid, report, *, start_at=""):
        raise provision.SetupError("vibe_setup_failed", "node")
    monkeypatch.setattr(provision, "setup", kaputt)
    with pytest.raises(jobs.JobError):
        run(jobs.create_and_setup(admin="boss", name="App", model=MODEL))
    pid = state.projects_of("boss")[0]["project_id"]
    assert container.name_for(pid) in env.containers                    # nichts weggeräumt: Nutzer sieht, was los ist
    run(projects.remove(pid, owner="boss"))
    assert state.projects_of("boss") == [] and not env.containers


def test_wiederholen_nach_failed_laeuft_ab_dem_fehlerschritt_neu(env, monkeypatch):
    zaehler = {"n": 0}
    starts: list[str] = []

    async def erst_kaputt(pid, report, *, start_at=""):
        zaehler["n"] += 1
        starts.append(start_at)
        report("user")
        if zaehler["n"] == 1:
            raise provision.SetupError("vibe_setup_failed", "packages")
    monkeypatch.setattr(provision, "setup", erst_kaputt)
    with pytest.raises(jobs.JobError):
        run(jobs.create_and_setup(admin="boss", name="App", model=MODEL))
    pid = state.projects_of("boss")[0]["project_id"]
    run(jobs.retry_setup(pid, owner="boss"))
    assert _row(pid)["state"] == "ready" and zaehler["n"] == 2
    assert starts == ["", "packages"]               # zweiter Lauf beginnt am Schritt, der scheiterte
    run(projects.remove(pid, owner="boss"))


def test_retry_nur_fuer_failed_und_nur_fuer_den_besitzer(env):
    out = run(jobs.create_and_setup(admin="boss", name="App", model=MODEL))
    with pytest.raises(jobs.JobError) as e:
        run(jobs.retry_setup(out["project_id"], owner="boss"))
    assert e.value.code == "vibe_not_failed"
    with pytest.raises(jobs.JobError) as e2:
        run(jobs.retry_setup(out["project_id"], owner="testuser"))
    assert e2.value.code == "vibe_project_not_found"
    run(projects.remove(out["project_id"], owner="boss"))


def test_nur_ein_auftrag_je_projekt(env, monkeypatch):
    gate = asyncio.Event()

    async def langsam(pid, report, *, start_at=""):
        report("user")
        await gate.wait()
    monkeypatch.setattr(provision, "setup", langsam)

    async def ablauf():
        t1 = asyncio.create_task(jobs.create_and_setup(admin="boss", name="A", model=MODEL))
        await asyncio.sleep(0.05)
        pid = state.projects_of("boss")[0]["project_id"]
        with pytest.raises(jobs.JobError) as e:
            await jobs.retry_setup(pid, owner="boss")
        gate.set()
        await t1
        return e.value.code, pid
    code, pid = run(ablauf())
    assert code == "vibe_busy"
    run(projects.remove(pid, owner="boss"))


def test_neustart_haelt_halbe_auftraege_fuer_unterbrochen(env):
    pid = "01a1-test"
    state.add_row(project_id=pid, agent_id="a", container="hh-vibe-x", name="Halb", owner="boss")
    state.set_state(pid, "setting_up")
    jobs.recover_after_restart()
    r = _row(pid)
    assert r["state"] == "failed" and r["error_code"] == "vibe_interrupted"
    state.delete_row(pid)


def test_neustart_laesst_fertige_projekte_in_ruhe(env):
    pid = "01a1-ready"
    state.add_row(project_id=pid, agent_id="a", container="hh-vibe-y", name="Fertig", owner="boss")
    state.set_state(pid, "ready")
    jobs.recover_after_restart()
    assert _row(pid)["state"] == "ready"
    state.delete_row(pid)


def test_state_zeigt_fortschritt_ohne_interna(env, client, admin_headers):
    out = run(jobs.create_and_setup(admin="boss", name="App", model=MODEL))
    row = client.get("/api/modules/vibe/state", headers=admin_headers).json()["projects"][0]
    assert row["state"] == "ready" and {"progress", "error_code", "error_step"} <= set(row)
    assert "container" not in row and "agent_id" not in row
    run(projects.remove(out["project_id"], owner="boss"))


def test_busy_wird_auch_bei_failed_zustand_abgelehnt(env):
    """Die Sperre „ein Auftrag je Projekt“ gilt unabhängig vom Zustand in der Datenbank."""
    pid = "01a1-busy"
    state.add_row(project_id=pid, agent_id="a", container="hh-vibe-z", name="B", owner="boss")
    state.set_state(pid, "failed", error_code="vibe_setup_failed", error_step="node")
    jobs._busy.add(pid)
    with pytest.raises(jobs.JobError) as e:
        run(jobs.retry_setup(pid, owner="boss"))
    assert e.value.code == "vibe_busy"
    jobs._busy.discard(pid)
    state.delete_row(pid)


# --- Fehlerausgabe festhalten (an hydratest 5.11. gefunden: npm ci scheiterte einmal ohne jede Spur) -----------------

def test_migration_hat_spalte_error_detail(db_ready):
    from hydrahive.db.connection import db
    with db() as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(module_vibe_projects)")}
    assert "error_detail" in cols


def test_fehlerdetail_wird_gespeichert(env, monkeypatch):
    async def kaputt(pid, report, *, start_at=""):
        raise provision.SetupError("vibe_setup_failed", "deps", "npm error network request failed")
    monkeypatch.setattr(provision, "setup", kaputt)
    with pytest.raises(jobs.JobError) as e:
        run(jobs.create_and_setup(admin="boss", name="App", model=MODEL))
    assert e.value.detail == "npm error network request failed"
    row = state.projects_of("boss")[0]
    assert row["error_detail"] == "npm error network request failed" and row["error_step"] == "deps"


def test_fehlerdetail_kommt_in_state_fuer_die_oberflaeche(env, client, admin_headers, monkeypatch):
    async def kaputt(pid, report, *, start_at=""):
        raise provision.SetupError("vibe_setup_failed", "deps", "npm error network request failed")
    monkeypatch.setattr(provision, "setup", kaputt)
    with pytest.raises(jobs.JobError):
        run(jobs.create_and_setup(admin="boss", name="App", model=MODEL))
    row = client.get("/api/modules/vibe/state", headers=admin_headers).json()["projects"][0]
    assert row["error_detail"] == "npm error network request failed"


def test_fehlerdetail_wird_nach_erfolgreichem_wiederholen_geloescht(env, monkeypatch):
    n = {"i": 0}

    async def erst_kaputt(pid, report, *, start_at=""):
        n["i"] += 1
        if n["i"] == 1:
            raise provision.SetupError("vibe_setup_failed", "deps", "alter Fehler")
    monkeypatch.setattr(provision, "setup", erst_kaputt)
    with pytest.raises(jobs.JobError):
        run(jobs.create_and_setup(admin="boss", name="App", model=MODEL))
    pid = state.projects_of("boss")[0]["project_id"]
    run(jobs.retry_setup(pid, owner="boss"))
    row = state.projects_of("boss")[0]
    assert row["state"] == "ready" and row["error_detail"] == "" and row["error_code"] == ""


def test_fehlerdetail_bei_unterbrochenem_auftrag_ist_leer(env):
    state.add_row(project_id="01a1-detail", agent_id="a", container="hh-vibe-d", name="Halb", owner="boss")
    state.set_state("01a1-detail", "setting_up")
    jobs.recover_after_restart()
    assert state.get_row("01a1-detail")["error_detail"] == ""
    state.delete_row("01a1-detail")


def test_fehlerdetail_anderer_fehler_im_auftrag_hat_kein_detail(env, monkeypatch):
    async def boom(pid, report, *, start_at=""):
        raise RuntimeError("geheimer interner Text mit /var/lib/hydrahive2/pfad")
    monkeypatch.setattr(provision, "setup", boom)
    with pytest.raises(jobs.JobError) as e:
        run(jobs.create_and_setup(admin="boss", name="App", model=MODEL))
    assert e.value.detail == "" and "geheim" not in str(state.projects_of("boss")[0])


def test_fehlerdetail_ist_in_der_datenbank_begrenzt(env, monkeypatch):
    async def gross(pid, report, *, start_at=""):
        raise provision.SetupError("vibe_setup_failed", "deps", "x" * 5000)
    monkeypatch.setattr(provision, "setup", gross)
    with pytest.raises(jobs.JobError):
        run(jobs.create_and_setup(admin="boss", name="App", model=MODEL))
    assert len(state.projects_of("boss")[0]["error_detail"]) <= provision.MAX_DETAIL
