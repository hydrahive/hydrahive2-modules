"""Multiseat M2a (MS3, MS4): Plan, erzeugte Dateien, multiseat-apply.sh / multiseat-revert.sh mit Ersatzprogrammen.

Nichts hier ruft echte Systemprogramme mit Wirkung auf: PATH zeigt auf Ersatzprogramme, alle /etc-Pfade liegen unter
tmp (HH_MULTISEAT_ROOT). Rechnerdaten (PCI-Adressen, USB-Ports) stehen nur in der Fixture.
"""
from __future__ import annotations

import json
import re
import subprocess

import pytest
from _multiseat_env import (
    EXT,
    PLAIN,
    SESS_KIOSK_BOTH,
    SESS_NO_SEAT1,
    SESS_OK,
    Env,
    tills_plan,
)
from _seats_fixture import build
from backend import seat_plan
from backend.seats import SeatError

BACKEND = EXT.parent / "backend"
LIGHTDM = "lightdm/lightdm.conf.d/50-hydrahive-multiseat.conf"
XORG = "X11/xorg.conf.d/90-hydrahive-vitrine-seat0.conf"
BK = "hydrahive2-vitrine/multiseat-vorher"


@pytest.fixture
def env(tmp_path):
    return Env(tmp_path)


# --- MS3: Plan und Dateien aus Tills Aufbau ---------------------------------------------------------------------

def test_ms3_plan_aus_tills_aufbau(tmp_path):
    p = tills_plan(build(tmp_path))
    assert p["seat0_busid"] == "PCI:13:0:0"                         # 0000:0d:00.0 hexadezimal → dezimal (M0)
    assert p["seat0_driver"] == "amdgpu"
    assert p["evdi_kmsdev"] == "/dev/dri/by-path/platform-evdi.0-card"  # stabil statt card1
    assert p["attach"] == [
        "/sys/devices/pci0000:00/0000:00:01.1/0000:01:00.0",                              # NVIDIA, PCI-Funktion
        "/sys/devices/pci0000:00/0000:00:01.1/0000:01:00.1/sound/card0",                  # ihr HDMI-Ton
        "/sys/devices/pci0000:00/0000:00:02.1/0000:02:00.0/0000:03:0c.0/0000:0a:00.0/usb1/1-5",  # Rapoo: USB-GERÄT
    ]
    assert (p["kiosk_user"], p["kiosk_session"]) == ("hydrahive-kiosk", "hydrahive-vitrine-kiosk")


def _sections(text: str) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    cur = None
    for ln in text.splitlines():
        if ln.startswith("["):
            cur = out.setdefault(ln.strip("[]"), {})
        elif "=" in ln and cur is not None and not ln.startswith("#"):
            k, _, v = ln.partition("=")
            cur[k] = v
    return out


def test_ms3_lightdm_autologin_nur_seat0(tmp_path):
    s = _sections(seat_plan.render_lightdm(tills_plan(build(tmp_path))))
    assert s["Seat:seat0"] == {"autologin-user": "hydrahive-kiosk", "autologin-session": "hydrahive-vitrine-kiosk",
                               "autologin-user-timeout": "0"}
    assert s["Seat:seat1"] == {"greeter-session": "lightdm-gtk-greeter"}
    assert set(s) == {"Seat:seat0", "Seat:seat1"}                    # kein [Seat:*] → Autologin gilt nicht überall


def test_ms3_xorg_nach_m0(tmp_path):
    x = seat_plan.render_xorg(tills_plan(build(tmp_path)))
    assert 'BusID      "PCI:13:0:0"' in x and 'Driver     "amdgpu"' in x
    assert 'Option     "kmsdev" "/dev/dri/by-path/platform-evdi.0-card"' in x
    assert 'GPUDevice  "hh-vitrine-evdi"' in x
    assert x.count('MatchSeat  "seat0"') == 4 and "seat1" not in x


@pytest.mark.parametrize("pci, want", [("0000:0d:00.0", "PCI:13:0:0"), ("0000:1f:1c.7", "PCI:31:28:7"),
                                       ("0001:01:00.0", "PCI:1@1:0:0")])
def test_busid_dezimal(pci, want):
    assert seat_plan.xorg_busid(pci) == want


def test_unbekannter_treiber_wird_modesetting(tmp_path):
    p = {**tills_plan(build(tmp_path)), "seat0_driver": 'x"; rm -rf /'}
    assert 'Driver     "modesetting"' in seat_plan.render_xorg(p).split("hh-vitrine-evdi")[0]


def test_ms3_keine_festen_geraetepfade_im_code():
    """Allgemeingültig: keine PCI-Adressen, Kartennummern oder USB-Ports eines Rechners im Modulcode (nur Fixtures)."""
    bad = re.compile(r"[0-9a-f]{4}:[0-9a-f]{2}:[0-9a-f]{2}\.[0-7]|PCI:\d+:\d+:\d+|/dev/dri/card\d|usb\d/\d-\d|\bcard\d\b")
    for f in [*EXT.glob("multiseat-*.sh"), BACKEND / "seat_plan.py"]:
        hits = [ln for ln in f.read_text().splitlines() if bad.search(ln)]
        assert not hits, f"{f.name}: {hits}"
    assert "/usr/bin/sddm" not in (EXT / "multiseat-revert.sh").read_text()
    code = "\n".join(ln.split(" #")[0] for ln in (EXT / "multiseat-apply.sh").read_text().splitlines()
                     if not ln.lstrip().startswith("#"))
    assert "sddm" not in code.replace("SDDM_CONF", "").replace("sddm.conf", ""), \
        "apply kennt sddm nur als zu sichernde Datei; den aktiven Dienst liest es aus display-manager.service"


def test_plan_lehnt_bluetooth_an_seat1_ab(tmp_path):
    from _seats_fixture import BT_KB, K400, NV, RAPOO
    from backend import seats, seats_snapshot
    snap = seats_snapshot.read(build(tmp_path, inputs=BT_KB + K400 + RAPOO))
    a = {d["id"]: "seat0" for k in ("gpus", "sound", "inputs") for d in snap[k]}
    a.update({f"gpu:pci:{NV}": "seat1", "input:bt:aa:bb:cc:dd:ee:ff": "seat1"})
    with pytest.raises(SeatError) as e:
        seat_plan.build_plan(snap, seats.validate(snap, a))
    assert e.value.code == "vitrine_seat_plan_bt_seat1"


# --- Skript: Erfolg ---------------------------------------------------------------------------------------------

def test_apply_erfolg(env):
    r = env.run("multiseat-apply.sh", *env.write_plan())
    assert r.returncode == 0, r.stderr
    assert env.etc(LIGHTDM).read_text() == (env.files / "lightdm.conf").read_text()
    assert env.etc(XORG).read_text() == (env.files / "xorg.conf").read_text()
    assert env.etc("X11/default-display-manager").read_text().strip() == str(env.bin / "lightdm")   # command -v
    assert env.etc(f"{BK}/default-display-manager").read_text() == "/usr/bin/sddm\n"
    assert env.etc(f"{BK}/dm-unit").read_text() == "sddm.service\n"
    assert env.etc("hydrahive2-vitrine/multiseat.aktiv").exists()
    c = env.calls()
    assert "systemctl disable sddm.service" in c and "systemctl stop sddm.service" in c
    assert "systemctl enable --force lightdm.service" in c
    assert c[-1] == "systemctl stop hydrahive2-vitrine-multiseat-revert.timer"     # Sicherheitsnetz abgebaut
    assert sum(ln.startswith("loginctl attach seat1 /sys/devices/") for ln in c) == 3
    assert any(ln.startswith("apt-get -qq install -y --no-install-recommends lightdm lightdm-gtk-greeter") for ln in c)


# --- MS4: Rückbau -----------------------------------------------------------------------------------------------

def _idx(calls: list[str], prefix: str) -> int:
    return next(i for i, c in enumerate(calls) if c.startswith(prefix))


@pytest.mark.parametrize("sessions, firefox", [(SESS_NO_SEAT1, True), (SESS_KIOSK_BOTH, True), (SESS_OK, False)],
                         ids=["kein-anmeldebildschirm", "kiosk-auch-auf-seat1", "kein-firefox"])
def test_ms4_pruefung_scheitert_rueckbau(env, sessions, firefox):
    r = env.run("multiseat-apply.sh", *env.write_plan(), sessions=sessions, firefox=firefox)
    assert r.returncode == 1 and "Prüfung" in r.stderr and "NICHT eingeschaltet" in r.stderr
    assert not env.etc(LIGHTDM).exists() and not env.etc(XORG).exists()
    assert env.etc("X11/default-display-manager").read_text() == "/usr/bin/sddm\n"   # aus der Sicherung
    assert env.etc("sddm.conf").read_text() == PLAIN
    assert not list(env.etc("udev/rules.d").glob("72-seat-*"))                        # Gerätezuordnung zurück
    assert not env.etc(BK).exists() and not env.etc("hydrahive2-vitrine/multiseat.aktiv").exists()
    c = env.calls()
    timer = _idx(c, "systemd-run --quiet --unit=hydrahive2-vitrine-multiseat-revert --on-active=300 /bin/bash")
    assert timer < _idx(c, "loginctl attach") < _idx(c, "systemctl enable --force lightdm.service")
    after = c[_idx(c, "loginctl flush-devices"):]
    assert "systemctl enable --force sddm.service" in after and "systemctl restart sddm.service" in after
    assert "systemctl disable lightdm.service" in c


def test_ms4_dm_aus_der_sicherung_nicht_geraten(env):
    """Anderer Anmeldedienst vorher (gdm3 unter /usr/sbin) → genau der kommt zurück, kein sddm."""
    r = env.root
    (r / "etc/X11/default-display-manager").write_text("/usr/sbin/gdm3\n")
    (r / "usr/lib/systemd/system/gdm.service").write_text("[Unit]\n")
    link = r / "etc/systemd/system/display-manager.service"
    link.unlink()
    link.symlink_to(r / "usr/lib/systemd/system/gdm.service")
    res = env.run("multiseat-apply.sh", *env.write_plan(), sessions=SESS_NO_SEAT1)
    assert res.returncode == 1
    assert env.etc("X11/default-display-manager").read_text() == "/usr/sbin/gdm3\n"
    c = env.calls()
    assert "systemctl enable --force gdm.service" in c and not any("sddm.service" in x for x in c)


def test_ms4_timer_vor_dem_umschalten_auch_bei_erfolg(env):
    env.run("multiseat-apply.sh", *env.write_plan())
    c = env.calls()
    t = _idx(c, "systemd-run --quiet --unit=hydrahive2-vitrine-multiseat-revert")
    assert t < _idx(c, "loginctl attach") and t < _idx(c, "systemctl stop sddm.service")
    assert env.etc("hydrahive2-vitrine/multiseat-revert.sh").exists()                 # Ziel des Timers liegt bereit


def test_apt_fehler_schaltet_nichts_um(env):
    env.apt_fail.write_text("1")
    r = env.run("multiseat-apply.sh", *env.write_plan())
    assert r.returncode == 1 and "nichts umgeschaltet" in r.stderr
    assert not any(c.startswith(("loginctl attach", "systemctl", "systemd-run")) for c in env.calls())
    assert not env.etc(BK).exists() and env.etc("sddm.conf").read_text() == PLAIN


# --- Plan-Prüfung im Skript (vor jeder Änderung) ----------------------------------------------------------------

@pytest.mark.parametrize("bad", ["/etc/passwd", "/sys/devices/../../etc/passwd", "/sys/devices/pci0000:00/x;reboot",
                                 "/sys/devices/pci0000:00/$(id)", "/sys/devices/pci 00", "/sys/devices/gibtsnicht",
                                 "/sys/class/drm/card9"])
def test_apply_lehnt_schlechte_pfade_ab(env, bad):
    plan = tills_plan(env.root)
    plan["attach"] = [*plan["attach"], bad]
    r = env.run("multiseat-apply.sh", *env.write_plan(plan))
    assert r.returncode == 2, r.stderr
    assert env.calls() == [] and not env.etc(BK).exists() and not env.etc(LIGHTDM).exists()


def test_apply_lehnt_symlink_aus_sys_devices_hinaus_ab(env):
    (env.root / "sys/devices/raus").symlink_to(env.root / "etc")
    plan = tills_plan(env.root)
    plan["attach"].append("/sys/devices/raus")
    assert env.run("multiseat-apply.sh", *env.write_plan(plan)).returncode == 2 and env.calls() == []


@pytest.mark.parametrize("key, val", [("seat0_busid", "PCI:13:0:0\nX"), ("seat0_busid", "13:0:0"),
                                      ("evdi_kmsdev", "/etc/shadow"), ("evdi_kmsdev", "/dev/dri/../sda"),
                                      ("kiosk_user", "root;x")])
def test_apply_lehnt_schlechte_werte_ab(env, key, val):
    plan = {**tills_plan(env.root), key: val}
    assert env.run("multiseat-apply.sh", *env.write_plan(plan)).returncode == 2 and env.calls() == []


def test_apply_zweimal_ohne_ausschalten_abgelehnt(env):
    args = env.write_plan()
    env.etc(BK).mkdir(parents=True)
    r = env.run("multiseat-apply.sh", *args)
    assert r.returncode == 2 and "schon eingeschaltet" in r.stderr and env.calls() == []


# --- Rückbau einzeln --------------------------------------------------------------------------------------------

def test_revert_nach_erfolg_und_zweimal(env):
    assert env.run("multiseat-apply.sh", *env.write_plan()).returncode == 0
    r1 = env.run("multiseat-revert.sh", sessions=SESS_NO_SEAT1)
    assert r1.returncode == 0, r1.stderr
    assert env.etc("X11/default-display-manager").read_text() == "/usr/bin/sddm\n"
    assert not env.etc(LIGHTDM).exists() and not env.etc("hydrahive2-vitrine/multiseat.aktiv").exists()
    r2 = env.run("multiseat-revert.sh", sessions=SESS_NO_SEAT1)
    assert r2.returncode == 0 and "keine Sicherung" in r2.stderr
    tail = env.calls()[-3:]
    assert not any("enable" in c or "restart" in c for c in tail), "ohne Sicherung wird kein Anmeldedienst geraten"
    assert env.etc("X11/default-display-manager").read_text() == "/usr/bin/sddm\n"


def test_revert_stellt_eigene_vorherige_lightdm_datei_wieder_her(env):
    env.etc("lightdm/lightdm.conf.d").mkdir(parents=True)
    env.etc("lightdm/lightdm.conf.d/50-hydrahive-extra.conf").write_text("[Seat:*]\n")
    env.run("multiseat-apply.sh", *env.write_plan(), sessions=SESS_NO_SEAT1)
    assert env.etc("lightdm/lightdm.conf.d/50-hydrahive-extra.conf").read_text() == "[Seat:*]\n"


def test_plan_json_ist_was_das_skript_liest(tmp_path):
    p = tills_plan(build(tmp_path))
    assert json.loads(seat_plan.plan_json(p)) == p


def test_shell_syntax_multiseat():
    for f in sorted(EXT.glob("multiseat-*.sh")):
        subprocess.run(["bash", "-n", str(f)], check=True)
