"""Multiseat nach Live-Test 2 (24.11.2026 20:20, MS4): Geräte samt Kindern wirklich an seat1.

Befund am Server: Nach `loginctl attach` lagen die 72-seat-Regeln richtig, aber nur die Grafikkarte hatte ID_SEAT=seat1.
Maus-Empfänger (USB), seine input/hidraw-Kinder und die Tonkarten nicht → Xorg von seat0 übernahm die Maus; die Prüfung
bestand trotzdem. Reparatur am Server: udevadm control --reload + trigger --action=change --settle auf die Pfade und
--parent-match (Kinder). Der Ersatz-udevadm (_multiseat_env.py) wendet Regeln nur nach --reload an und erreicht Kinder
nur über --parent-match – genau wie am Server beobachtet.
"""
from __future__ import annotations

import pytest
from _multiseat_env import SESS_NO_SEAT1, Env

BK = "hydrahive2-vitrine/multiseat-vorher"


@pytest.fixture
def env(tmp_path):
    return Env(tmp_path)


def _seat1(env) -> set[str]:
    return {"/" + str(p.parent.relative_to(env.root)) for p in env.root.rglob(".seat1")}


def _seat_tagged(env) -> set[str]:
    return {p for p, seat in env.udev_devices.items() if seat}


def _idx(c: list[str], prefix: str, start: int = 0) -> int:
    return next(i for i, x in enumerate(c) if i >= start and x.startswith(prefix))


def test_apply_triggert_geraete_und_kinder_nach_attach(env):
    r = env.run("multiseat-apply.sh", *env.write_plan())
    assert r.returncode == 0, r.stderr
    c = env.calls()
    last_attach = max(i for i, x in enumerate(c) if x.startswith("loginctl attach"))
    reload = _idx(c, "udevadm control --reload")
    assert last_attach < reload < _idx(c, "systemctl enable --force lightdm.service")
    attach = [x.split()[-1] for x in c if x.startswith("loginctl attach")]
    for p in attach:
        own = c.index(f"udevadm trigger --action=change --settle {p}")
        kids = c.index(f"udevadm trigger --action=change --settle --parent-match={p}")
        assert reload < own < kids                                     # erst das Gerät, dann die Kinder
    assert _seat1(env) == _seat_tagged(env)                            # alle seat-Geräte samt Kindern an seat1
    assert any(p.endswith("/event16") for p in _seat1(env)) and any("/hidraw/" in p for p in _seat1(env))


def test_apply_prueft_id_seat_jedes_geraets(env):
    env.run("multiseat-apply.sh", *env.write_plan())
    infos = {x.split("--path=")[1] for x in env.calls() if x.startswith("udevadm info -q property --path=")}
    assert _seat_tagged(env) <= infos                                  # jedes seat-getaggte Gerät gefragt


def test_kind_ohne_seat1_prueffehler_rueckbau(env, tmp_path):
    """Ein Kind (Maus-Ereignisgerät) bleibt ohne ID_SEAT – wie am Server ohne --parent-match → fail + Rückbau."""
    fake = env.bin / "udevadm"
    fake.write_text(fake.read_text().replace('"udevadm trigger")', '"udevadm trigger")\n    case "$*" in *parent-match=*usb*) exit 0;; esac'))
    r = env.run("multiseat-apply.sh", *env.write_plan())
    assert r.returncode == 1, r.stderr
    assert "nicht beim zweiten Arbeitsplatz" in r.stderr and "/usb1/1-5/1-5:1.0/" in r.stderr   # ein Kind, nicht das Gerät
    c = env.calls()
    assert not any(x == "systemctl enable --force lightdm.service" for x in c)   # vor dem DM-Wechsel abgebrochen
    assert "loginctl flush-devices" in c and not env.etc(BK).exists()
    assert not list(env.etc("udev/rules.d").glob("72-seat-*"))


def test_ohne_reload_greift_trigger_nicht(env):
    """Gegenstück zum Befund: Regeln liegen, aber ohne control --reload wendet udev sie nicht an → Prüfung scheitert."""
    fake = env.bin / "udevadm"
    fake.write_text(fake.read_text().replace('[ "$2" = "--reload" ] && touch "$R/.udev-geladen"', ":"))
    r = env.run("multiseat-apply.sh", *env.write_plan())
    assert r.returncode == 1 and "ID_SEAT fehlt" in r.stderr


def test_revert_gibt_geraete_per_trigger_zurueck(env):
    assert env.run("multiseat-apply.sh", *env.write_plan()).returncode == 0
    attach = env.etc(f"{BK}/attach.liste").read_text().split()
    assert len(attach) == 3 and _seat1(env)
    env.log.write_text("")
    assert env.run("multiseat-revert.sh", sessions=SESS_NO_SEAT1).returncode == 0
    c = env.calls()
    flush = c.index("loginctl flush-devices")
    for p in attach:
        assert flush < c.index(f"udevadm trigger --action=change --settle --parent-match={p}")
    last_trigger = max(i for i, x in enumerate(c) if x.startswith("udevadm trigger"))
    assert last_trigger < c.index("udevadm settle --timeout=15") < c.index("systemctl enable --force sddm.service")
    assert _seat1(env) == set()                                         # niemand trägt mehr ID_SEAT=seat1


def test_revert_triggert_nur_gepruefte_pfade(env):
    assert env.run("multiseat-apply.sh", *env.write_plan()).returncode == 0
    liste = env.etc(f"{BK}/attach.liste")
    liste.write_text(liste.read_text() + "/etc/passwd\n/sys/devices/../../etc\n/sys/devices/x;reboot\n")
    env.log.write_text("")
    assert env.run("multiseat-revert.sh", sessions=SESS_NO_SEAT1).returncode == 0
    trig = [x for x in env.calls() if x.startswith("udevadm trigger")]
    assert len(trig) == 6 and not any("passwd" in x or ".." in x or ";" in x for x in trig)


def test_revert_ohne_liste_aus_alter_version(env):
    """Sicherung einer älteren Version ohne attach.liste: kein Trigger, Rückbau trotzdem vollständig."""
    assert env.run("multiseat-apply.sh", *env.write_plan()).returncode == 0
    env.etc(f"{BK}/attach.liste").unlink()
    env.log.write_text("")
    r = env.run("multiseat-revert.sh", sessions=SESS_NO_SEAT1)
    assert r.returncode == 0 and not any(x.startswith("udevadm trigger") for x in env.calls())
    assert "systemctl restart sddm.service" in env.calls()
