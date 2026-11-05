"""Baustein 7: Platzgrenze (PLAN-V1.md Entscheidung 5).

`size=` greift auf dem `dir`-Pool nicht; das Modul misst darum selbst mit einem fest eingetragenen Befehl im Container.
Über der Grenze (5 GB) wird kein Agentenlauf mehr gestartet und im Chat steht, was zu groß ist. Das ist KEIN lückenloser
Schutz (ein Lauf kann innerhalb einer Runde füllen); er verhindert nur, dass ein voller Container weiter bearbeitet wird.
"""
from __future__ import annotations

import asyncio

import pytest
from backend import container, guard, network, projects, state

MODEL = "claude-sonnet-4-6"
GB = 1024 ** 3


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
def pid(env):
    out = run(projects.create(admin="boss", name="Platz", model=MODEL))
    yield out["project_id"]
    run(projects.remove(out["project_id"], owner="boss"))


def _du(env, kib: int) -> None:
    env.exec_answers["du -sk"] = (0, f"{kib}\t/work\n")


def test_grenze_ist_fuenf_gigabyte():
    assert guard.MAX_BYTES == 5 * GB


def test_unter_der_grenze_ok(env, pid):
    _du(env, 2 * 1024 * 1024)                              # 2 GB
    assert run(guard.check(pid)) == {"ok": True, "bytes": 2 * GB, "limit": 5 * GB}


def test_genau_auf_der_grenze_ist_noch_ok(env, pid):
    _du(env, 5 * 1024 * 1024)
    assert run(guard.check(pid))["ok"] is True


def test_ueber_der_grenze_nicht_ok(env, pid):
    _du(env, 5 * 1024 * 1024 + 1)
    r = run(guard.check(pid))
    assert r["ok"] is False and r["bytes"] == 5 * GB + 1024


def test_messung_ist_ein_fester_befehl_ohne_eingaben(env, pid):
    _du(env, 1)
    run(guard.check(pid))
    cmds = [" ".join(c) for c in env.calls if c and c[0] == "exec"]
    du = [c for c in cmds if "du -sk" in c]
    assert du and all("/work" in c and pid not in c.split("--", 1)[1] for c in du)


def test_messung_laeuft_im_richtigen_container_als_nutzer(env, pid):
    _du(env, 1)
    run(guard.check(pid))
    call = [c for c in env.calls if c[0] == "exec" and "du -sk" in " ".join(c)][-1]
    assert call[1] == container.name_for(pid)


def test_unlesbare_ausgabe_gilt_nicht_als_ok(env, pid):
    """Lieber einmal zu streng als einen vollen Container weiterbearbeiten."""
    env.exec_answers["du -sk"] = (0, "Quatsch\n")
    r = run(guard.check(pid))
    assert r["ok"] is False and r["bytes"] is None


def test_befehl_scheitert_gilt_nicht_als_ok(env, pid):
    env.exec_answers["du -sk"] = (1, "")
    assert run(guard.check(pid))["ok"] is False


def test_negative_oder_riesige_zahl_wird_abgelehnt(env, pid):
    for bad in ("-5\t/work", "9" * 40 + "\t/work"):
        env.exec_answers["du -sk"] = (0, bad + "\n")
        assert run(guard.check(pid))["ok"] is False


def test_text_fuer_den_chat_nennt_groesse_und_grenze_ohne_pfade(env, pid):
    _du(env, 6 * 1024 * 1024)
    t = guard.message(run(guard.check(pid)))
    assert "6" in t and "5" in t and "GB" in t and "/work" not in t and pid not in t


def test_meldung_nennt_was_zu_gross_ist(env, pid):
    _du(env, 6 * 1024 * 1024)
    env.exec_answers["du -s"] = (0, "")
    big = "4194304\tnode_modules\n2097152\tdist\n"
    env.exec_answers["du -sk --"] = (0, big)
    r = run(guard.check(pid, detail=True))
    assert r["ok"] is False and [d["name"] for d in r["top"]][:2] == ["node_modules", "dist"]


def test_top_namen_werden_bereinigt(env, pid):
    _du(env, 6 * 1024 * 1024)
    env.exec_answers["du -sk --"] = (0, "100\t" + "A" * 300 + "\n100\t\x1b[31mrot\n")
    names = [d["name"] for d in run(guard.check(pid, detail=True))["top"]]
    assert all(len(n) <= 80 and "\x1b" not in n for n in names)


def test_nur_vibe_container_werden_gemessen(env):
    with pytest.raises(container.VibeError):
        run(guard.check("../etc"))
