"""Baustein 7: Ruhe – nach 30 min ohne Nutzung wird der Container gestoppt, eine Anfrage weckt ihn (SPEC.md).

Der Kern startet einen gestoppten Container NICHT von selbst (tools/_launcher_container.py: „Container aus → Fehler“),
darum muss das Modul ihn vor jedem Agentenlauf wecken. Zeitlimit 60 s, danach `vibe_container_down`.
"""
from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime, timedelta

import pytest
from backend import container, idle, network, projects, state

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


@pytest.fixture
def pid(env, monkeypatch):
    out = run(projects.create(admin="boss", name="Ruhe", model=MODEL))
    state.set_state(out["project_id"], "ready")
    yield out["project_id"]
    run(projects.remove(out["project_id"], owner="boss"))


def _age(pid: str, minutes: float) -> None:
    ts = (datetime.now(UTC) - timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")
    state.touch(pid, ts)


def _running(env, pid) -> bool:
    return env.containers[container.name_for(pid)]["running"]


def test_leerlauf_ist_30_minuten():
    assert idle.IDLE_MINUTES == 30


def test_frisch_benutzt_bleibt_an(env, pid):
    _age(pid, 5)
    run(idle.sweep())
    assert _running(env, pid)


def test_29_minuten_bleibt_an(env, pid):
    _age(pid, 29)
    run(idle.sweep())
    assert _running(env, pid)


def test_31_minuten_wird_gestoppt(env, pid):
    _age(pid, 31)
    run(idle.sweep())
    assert not _running(env, pid)
    assert state.get_row(pid)["state"] == "sleeping"


def test_schon_gestoppt_wird_nicht_nochmal_gestoppt(env, pid):
    _age(pid, 60)
    run(idle.sweep())
    n = len([c for c in env.calls if c[0] == "stop"])
    run(idle.sweep())
    assert len([c for c in env.calls if c[0] == "stop"]) == n


def test_laufender_zug_haelt_den_container_wach(env, pid, monkeypatch):
    _age(pid, 120)
    monkeypatch.setattr(idle, "_busy", lambda p: True)
    run(idle.sweep())
    assert _running(env, pid)


def test_einrichtung_laeuft_nicht_abschalten(env, pid):
    state.set_state(pid, "setting_up")
    _age(pid, 120)
    run(idle.sweep())
    assert _running(env, pid)


def test_failed_projekt_wird_nicht_angefasst(env, pid):
    state.set_state(pid, "failed", error_code="vibe_setup_failed", error_step="node")
    _age(pid, 120)
    run(idle.sweep())
    assert _running(env, pid)


def test_ein_fehler_bei_einem_projekt_stoppt_die_anderen_nicht(env, pid, monkeypatch):
    out2 = run(projects.create(admin="boss", name="Zwei", model=MODEL))
    state.set_state(out2["project_id"], "ready")
    _age(pid, 90)
    _age(out2["project_id"], 90)
    orig = container.stop

    async def mal_kaputt(p):
        if p == pid:
            raise RuntimeError("incus hängt")
        await orig(p)
    monkeypatch.setattr(idle.container, "stop", mal_kaputt)
    run(idle.sweep())
    assert not _running(env, out2["project_id"])
    run(projects.remove(out2["project_id"], owner="boss"))


def test_wecken_startet_den_container(env, pid):
    _age(pid, 60)
    run(idle.sweep())
    run(idle.wake(pid))
    assert _running(env, pid) and state.get_row(pid)["state"] == "ready"


def test_wecken_eines_laufenden_ist_ein_nichtstun(env, pid):
    run(idle.wake(pid))
    assert not [c for c in env.calls if c[0] == "start"]


def test_wecken_aktualisiert_die_letzte_nutzung(env, pid):
    _age(pid, 60)
    run(idle.sweep())
    run(idle.wake(pid))
    last = datetime.strptime(state.get_row(pid)["last_used_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    assert datetime.now(UTC) - last < timedelta(minutes=1)


def test_wecken_wartet_bis_der_container_antwortet(env, pid, monkeypatch):
    _age(pid, 60)
    run(idle.sweep())
    answers = iter([1, 1, 0])
    orig = env.run

    async def slow(*a, **kw):
        if a and a[0] == "exec" and "ip -4" in " ".join(a):
            return next(answers), "", ""
        return await orig(*a, **kw)
    monkeypatch.setattr(idle.incus, "run", slow)
    monkeypatch.setattr(idle.container.incus, "run", slow)

    async def no_sleep(_s):
        return None
    monkeypatch.setattr(idle.asyncio, "sleep", no_sleep)
    run(idle.wake(pid))
    assert _running(env, pid)


def test_wecken_zeitlimit_60s_dann_container_down(env, pid, monkeypatch):
    _age(pid, 60)
    run(idle.sweep())
    assert idle.WAKE_TIMEOUT == 60

    async def never(*a, **kw):
        return 1, "", "no address"
    monkeypatch.setattr(idle.container, "wait_for_address", lambda p: asyncio.sleep(3600))
    monkeypatch.setattr(idle, "WAKE_TIMEOUT", 0.2)
    with pytest.raises(container.VibeError) as e:
        run(idle.wake(pid))
    assert e.value.code == "vibe_container_down"


def test_wecken_unbekanntes_projekt(env):
    with pytest.raises(container.VibeError):
        run(idle.wake("01a1-gibtsnicht"))


def test_nach_dem_wecken_ist_der_dev_server_wieder_da(env, pid):
    """Der Dev-Server ist ein systemd-Dienst (enable --now): startet mit dem Container. Das Wecken prüft das nach."""
    _age(pid, 60)
    run(idle.sweep())
    env.exec_answers["curl -s -o /dev/null -m 1 http://127.0.0.1:5173/"] = (0, "")
    run(idle.wake(pid))
    assert any("5173" in " ".join(c) for c in env.calls if c[0] == "exec")


def test_beruehren_setzt_die_zeit_neu(env, pid):
    _age(pid, 50)
    state.touch(pid)
    assert datetime.now(UTC) - datetime.strptime(state.get_row(pid)["last_used_at"], "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=UTC) < timedelta(minutes=1)


def test_sweep_interval_ist_eine_minute():
    assert idle.SWEEP_SECONDS == 60
