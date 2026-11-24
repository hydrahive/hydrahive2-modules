"""Multiseat nach Live-Test 1 (24.11.2026, MS4): Dashboard-Drop-in in apply, Rückbau wartet auf udev/logind.

Befund am Server: (A) ein Update mit angeschlossenem Fernseher schrieb die Vitrine-Unit ohne VITRINE_KIOSK_DISPLAY →
EVDI blieb aus, die Prüfung in apply konnte nie bestehen. (B) revert startete sddm, während die Grafikkarte noch an
seat1 hing → Xorg auf seat0 brach ab, der Kiosk landete auf seat1. Ersatzprogramme wie test_multiseat_apply.py.
"""
from __future__ import annotations

import pytest
from _multiseat_env import SESS_NO_SEAT1, SESS_OK, Env

DROPIN = "systemd/system/hydrahive2-vitrine.service.d/50-hydrahive-multiseat.conf"
DROPIN_TEXT = ("[Service]\nEnvironment=VITRINE_KIOSK_DISPLAY=:0\nSupplementaryGroups=video\n"
               "BindReadOnlyPaths=-/tmp/.X11-unix\n")
SESS_KIOSK_SEAT1 = "93 1003 hydrahive-kiosk seat1 53800 user - no -\n"       # Kiosk auf dem Fernseher gelandet


@pytest.fixture
def env(tmp_path):
    return Env(tmp_path)


def _idx(calls: list[str], line: str, start: int = 0) -> int:
    return next(i for i, c in enumerate(calls) if i >= start and c == line)


def _apply_ok(env) -> None:
    r = env.run("multiseat-apply.sh", *env.write_plan())
    assert r.returncode == 0, r.stderr
    env.log.write_text("")                                     # nur die Aufrufe des Rückbaus betrachten


# --- (A) apply: Drop-in vor dem Umschalten, Vitrine-Neustart nach dem DM-Wechsel ------------------------------------

def test_apply_schreibt_dropin_vor_dem_umschalten(env):
    r = env.run("multiseat-apply.sh", *env.write_plan())
    assert r.returncode == 0, r.stderr
    assert env.etc(DROPIN).read_text() == DROPIN_TEXT
    assert env.etc(DROPIN).stat().st_mode & 0o777 == 0o644
    c = env.calls()
    reload = _idx(c, "systemctl daemon-reload")
    assert reload < next(i for i, x in enumerate(c) if x.startswith("loginctl attach"))
    assert reload < _idx(c, "systemctl enable --force lightdm.service")
    assert next(i for i, x in enumerate(c) if x.startswith("systemd-run")) < reload   # Timer vorher
    assert env.etc("hydrahive2-vitrine/multiseat-vorher/vitrine-dropin.conf.fehlt").exists()


def test_apply_startet_vitrine_nach_dem_dm_wechsel(env):
    env.run("multiseat-apply.sh", *env.write_plan())
    c = env.calls()
    assert _idx(c, "systemctl restart lightdm.service") < _idx(c, "systemctl restart hydrahive2-vitrine")


# --- (A) revert: Drop-in wie vorher ---------------------------------------------------------------------------------

def test_revert_entfernt_dropin_der_vorher_fehlte(env):
    r = env.run("multiseat-apply.sh", *env.write_plan(), sessions=SESS_NO_SEAT1)    # Prüfung scheitert → Rückbau
    assert r.returncode == 1
    assert not env.etc(DROPIN).exists() and not env.etc(DROPIN).parent.exists()
    c = env.calls()
    after = c[_idx(c, "systemctl restart sddm.service"):]
    assert "systemctl restart hydrahive2-vitrine" in after                       # Stand ohne Drop-in wird wirksam


def test_revert_stellt_vorhandenen_dropin_wieder_her(env):
    env.etc(DROPIN).parent.mkdir(parents=True)
    env.etc(DROPIN).write_text("[Service]\nEnvironment=EIGEN=1\n")
    _apply_ok(env)
    assert env.etc(DROPIN).read_text() == DROPIN_TEXT
    assert env.run("multiseat-revert.sh", sessions=SESS_NO_SEAT1).returncode == 0
    assert env.etc(DROPIN).read_text() == "[Service]\nEnvironment=EIGEN=1\n"


def test_revert_ohne_sicherung_entfernt_dropin(env):
    env.etc(DROPIN).parent.mkdir(parents=True)
    env.etc(DROPIN).write_text(DROPIN_TEXT)
    r = env.run("multiseat-revert.sh", sessions=SESS_NO_SEAT1)
    assert r.returncode == 0 and not env.etc(DROPIN).exists()
    assert not any(c.startswith("systemctl enable") for c in env.calls())       # Anmeldedienst nicht geraten


# --- (B) revert: erst seat1 weg, dann Anmeldedienst -----------------------------------------------------------------

def test_revert_wartet_auf_seat1_vor_dm_start(env):
    _apply_ok(env)
    env.seat1.write_text("2")                                  # logind meldet seat1 noch zweimal
    r = env.run("multiseat-revert.sh", sessions=SESS_NO_SEAT1)
    assert r.returncode == 0, r.stderr
    c = env.calls()
    flush = _idx(c, "loginctl flush-devices")
    settle = _idx(c, "udevadm settle --timeout=15")
    seats = [i for i, x in enumerate(c) if x == "loginctl list-seats --no-legend"]
    enable = _idx(c, "systemctl enable --force sddm.service")
    assert flush < settle < seats[0] and len(seats) == 3 and seats[-1] < enable
    assert c[seats[0]:seats[-1]].count("sleep 1") == 2                         # sichtbar gewartet
    assert enable < _idx(c, "systemctl restart sddm.service") < _idx(c, "systemctl restart hydrahive2-vitrine")


def test_revert_seat1_bleibt_zweites_flush(env, monkeypatch):
    _apply_ok(env)
    env.seat1.write_text("21")                                 # länger als 20 s → noch einmal zurückgeben
    r = env.run("multiseat-revert.sh", sessions=SESS_NO_SEAT1)
    assert r.returncode == 0 and "noch einmal zurückgeben" in r.stderr
    c = env.calls()
    enable = _idx(c, "systemctl enable --force sddm.service")
    assert c[:enable].count("loginctl flush-devices") == 2 and c[:enable].count("udevadm settle --timeout=15") == 2


def test_revert_wiederholt_einmal_wenn_kiosk_nicht_auf_seat0(env):
    _apply_ok(env)
    (env.tmp / "sessions.retry").write_text(SESS_NO_SEAT1)    # nach dem 2. sddm-Neustart ist der Kiosk auf seat0
    r = env.run("multiseat-revert.sh", sessions=SESS_KIOSK_SEAT1)
    assert r.returncode == 0, r.stderr
    c = env.calls()
    first = _idx(c, "systemctl restart sddm.service")
    second = _idx(c, "systemctl restart sddm.service", first + 1)
    between = c[first:second]
    assert "loginctl flush-devices" in between and "udevadm settle --timeout=15" in between
    assert between.index("loginctl flush-devices") < between.index("udevadm settle --timeout=15")
    assert c.count("systemctl restart sddm.service") == 2
    assert "Vitrine läuft wieder (seat0)" in r.stdout


def test_revert_wiederholt_nur_einmal_dann_exit3(env):
    _apply_ok(env)
    r = env.run("multiseat-revert.sh", sessions=SESS_KIOSK_SEAT1)
    assert r.returncode == 3 and "Rechner neu starten" in r.stderr
    assert env.calls().count("systemctl restart sddm.service") == 2


def test_revert_erfolg_ohne_wiederholung(env):
    _apply_ok(env)
    assert env.run("multiseat-revert.sh", sessions=SESS_OK).returncode == 0
    c = env.calls()
    assert c.count("systemctl restart sddm.service") == 1 and c.count("loginctl flush-devices") == 1
