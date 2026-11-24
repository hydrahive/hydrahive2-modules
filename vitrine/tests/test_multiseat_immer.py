"""§7 „Vitrine und Desktop immer“ (MS10): N1 Kiosk auch mit Monitor, N2a Automatik beim Update, N2b Monitor bleibt an.

Installer mit Ersatzprogrammen (_installer_env), Automatik backend.seat_auto mit nachgestellten Systemdaten
(_seats_fixture) und ersetztem subprocess.run; kiosk-session.sh mit Ersatz-xrandr. Nichts läuft als root.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest
from _installer_env import _ETC, EXT, Installer
from _seats_fixture import NV, build

from backend import seat_auto, seats_snapshot

AUTO = "venv-python -m backend.seat_auto"


# --- N1 / N2a im Installer -------------------------------------------------------------------------------------------

def test_n1_monitor_kiosk_wie_ohne_monitor(tmp_path):
    """Gewollte Abweichung zu 0.17.6: mit Monitor wird der Kiosk jetzt genau so eingerichtet wie ohne – plus Monitor-
    Vermerk für kiosk-session.sh (N2b) und Aufruf der Automatik (N2a)."""
    ohne, mit = Installer(tmp_path / "ohne"), Installer(tmp_path / "mit", monitor=True)
    assert ohne.run().returncode == 0 and mit.run().returncode == 0
    c_mit = mit.calls()
    assert c_mit[-1].startswith(AUTO) and AUTO not in "\n".join(ohne.calls())
    norm = [c.replace(" 'card2-HDMI-A-1'", "").replace(" card2-HDMI-A-1", "") for c in c_mit[:-1]]
    assert norm == ohne.calls()
    f_ohne, f_mit = ohne.files(), mit.files()
    assert f_mit.pop(f"{_ETC.lstrip('/')}/monitor-an") == "card2-HDMI-A-1\n"
    assert f_mit == f_ohne
    assert "VITRINE_KIOSK_DISPLAY=:0" in f_mit["etc/systemd/system/hydrahive2-vitrine.service"]


@pytest.mark.parametrize("kw, extra, why", [
    ({"monitor": True, "multiseat": True}, None, "Marker: schon an"),
    ({}, None, "kein Monitor"),
    ({"monitor": True}, "kiosk.off", "Kiosk abgeschaltet → kein Dashboard, nichts umschalten"),
])
def test_n2a_automatik_nicht_aufgerufen(tmp_path, kw, extra, why):
    inst = Installer(tmp_path, **kw)
    if extra:
        (tmp_path / "data/vitrine" / extra).write_text("")
    assert inst.run().returncode == 0
    assert not any(c.startswith(AUTO) for c in inst.calls()), why


def test_n2a_automatik_mit_datenordner_aus_dem_modul(tmp_path):
    inst = Installer(tmp_path, monitor=True)
    inst.run()
    call = next(c for c in inst.calls() if c.startswith(AUTO))
    assert call == f"{AUTO} <T>/data/vitrine"                         # nur der Datenordner, kein Nutzereingabe-Weg


def test_n1_evdi_ausgang_ist_kein_monitor(tmp_path):
    """Am Server zeigt card1-DVI-I-1/device auf die Karte, deren device auf evdi.0 (24.11.). Ein verbundenes
    USB-Display darf nicht als „echter Monitor“ gelten."""
    inst = Installer(tmp_path)
    drm = inst.root / "sys/class/drm"
    plat = inst.root / "sys/devices/platform/evdi.0"
    (plat / "drm/card1/card1-DVI-I-1").mkdir(parents=True)
    (inst.root / "sys/bus/platform/drivers/evdi").mkdir(parents=True)
    (plat / "driver").symlink_to(inst.root / "sys/bus/platform/drivers/evdi")
    (plat / "drm/card1/device").symlink_to(plat)
    out = plat / "drm/card1/card1-DVI-I-1"
    (out / "device").symlink_to(plat / "drm/card1")
    (out / "status").write_text("connected\n")
    (drm / "card1-DVI-I-1").symlink_to(out)
    assert inst.run().returncode == 0
    assert not (inst.root / _ETC.lstrip("/") / "monitor-an").exists()
    assert not any(c.startswith(AUTO) for c in inst.calls())


def test_n2b_monitor_vermerk_verschwindet_ohne_monitor(tmp_path):
    inst = Installer(tmp_path, monitor=True)
    inst.run()
    mark = inst.root / _ETC.lstrip("/") / "monitor-an"
    assert mark.exists()
    for f in (inst.root / "sys/class/drm").glob("card2-*"):
        (f / "status").write_text("disconnected\n")
    inst.run()
    assert not mark.exists()


# --- N2a: Automatik backend.seat_auto --------------------------------------------------------------------------------

class Run:
    def __init__(self, code: int = 0):
        self.calls: list[list[str]] = []
        self.code = code

    def __call__(self, cmd, **kw):
        self.calls.append(cmd)
        return subprocess.CompletedProcess(cmd, self.code, stdout="ok\n", stderr="")


@pytest.fixture
def auto(tmp_path, monkeypatch):
    run = Run()
    monkeypatch.setattr(seat_auto.subprocess, "run", run)
    d = tmp_path / "data"
    d.mkdir()
    etc = tmp_path / "etc"
    etc.mkdir()

    def go(*, tv: bool = True, saved: dict | None | bool = True, marker: bool = False) -> str:
        root = build(tmp_path / f"sys{len(run.calls)}{tv}", tv=tv)
        if saved is True:
            snap = seats_snapshot.read(root)
            a = {x["id"]: "seat0" for k in ("gpus", "sound", "inputs") for x in snap[k]}
            a.update({f"gpu:pci:{NV}": "seat1", f"sound:pci:{NV[:-1]}1": "seat1", "input:usb:1-5": "seat1"})
            saved = {"assignment": a, "saved_at": 1}
        if saved:
            (d / "seats.json").write_text(json.dumps(saved))
        if marker:
            (etc / "multiseat.aktiv").write_text("x\n")
        return seat_auto.auto_apply(d, sys_root=root, etc=etc)

    go.run, go.data = run, d
    return go


def test_ms10_monitor_und_gueltig_schaltet_ein(auto):
    assert auto() == "applied"
    (cmd,) = auto.run.calls
    d = auto.data / "multiseat"
    assert cmd[:4] == ["sudo", "-n", "bash", "-c"]
    assert cmd[4] == ("systemd-run --quiet --wait --pipe --collect /bin/bash "
                      f"{seat_auto.MODULE_ROOT / 'extension/multiseat-apply.sh'} {d / 'plan.json'} {d / 'lightdm.conf'} "
                      f"{d / 'xorg.conf'}")
    assert json.loads((d / "plan.json").read_text())["seat0_busid"] == "PCI:13:0:0"
    last = json.loads((d / "last-run.json").read_text())
    assert last["action"] == "apply" and last["source"] == "update" and last["ok"] is True


def test_ms10_auto_false_bleibt_aus(auto):
    saved = {"assignment": {"x": "seat0"}, "saved_at": 1, "auto": False}
    assert auto(saved=saved) == "auto_off" and auto.run.calls == []


def test_ms10_auto_true_und_ohne_vermerk_schalten_ein(auto):
    assert auto() == "applied"                                         # Tills seats.json hat noch kein auto
    s = json.loads((auto.data / "seats.json").read_text())
    s["auto"] = True
    (auto.data / "seats.json").write_text(json.dumps(s))
    assert seat_auto.read_saved(auto.data)["auto"] is True


@pytest.mark.parametrize("kw, want", [({"saved": False}, "not_saved"), ({"marker": True}, "already_on"),
                                      ({"tv": False}, "no_monitor"),
                                      ({"saved": {"assignment": {"input:usb:9-9": "seat1"}}}, "invalid:vitrine_seat_unknown_device")])
def test_ms10_kein_einschalten(auto, kw, want):
    assert auto(**kw) == want and auto.run.calls == []
    assert not (auto.data / "multiseat" / "plan.json").exists()


def test_ms10_fehlschlag_landet_in_last_run(auto):
    auto.run.code = 1
    assert auto() == "apply_failed:1"
    assert json.loads((auto.data / "multiseat/last-run.json").read_text())["exit"] == 1


def test_cli_bricht_installation_nie_ab(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(seat_auto, "auto_apply", lambda d: (_ for _ in ()).throw(RuntimeError("kaputt")))
    assert seat_auto.main(["x", str(tmp_path)]) == 0
    assert "Automatik übersprungen" in capsys.readouterr().err
    monkeypatch.setattr(seat_auto, "auto_apply", lambda d: "not_saved")
    assert seat_auto.main(["x", str(tmp_path)]) == 0 and "„Übernehmen“" in capsys.readouterr().out


# --- N2b: kiosk-session.sh -------------------------------------------------------------------------------------------

def _session(tmp_path: Path, *, monitor_an: bool, multiseat: bool) -> list[str]:
    conf, bin_, home = tmp_path / "conf", tmp_path / "bin", tmp_path / "home"
    for d in (conf, bin_, home / "vitrine"):
        d.mkdir(parents=True)
    log = tmp_path / "x.log"
    log.write_text("")
    if monitor_an:
        (conf / "monitor-an").write_text("card2-HDMI-A-1\n")
    if multiseat:
        (conf / "multiseat.aktiv").write_text("x\n")
    fakes = {
        "xrandr": 'echo "xrandr $*" >> "$L"; [ $# -eq 0 ] && printf "DVI-I-1-1 connected\\nHDMI-A-1 connected 3840x2160+0+0\\n"; exit 0',
        "xset": '[ "$1" = q ] && exit 1; exit 0', "xhost": "exit 0", "xsetroot": "exit 0", "openbox": "exit 0",
        "firefox": "exit 0", "sleep": "exit 0",
    }
    for name, body in fakes.items():
        (bin_ / name).write_text(f"#!/bin/bash\n{body}\n")
        (bin_ / name).chmod(0o755)
    env = {**os.environ, "PATH": f"{bin_}:/usr/bin:/bin", "HOME": str(home), "L": str(log), "VITRINE_CONF": str(conf)}
    subprocess.run(["bash", str(EXT / "kiosk-session.sh")], env=env, timeout=30, check=False)
    return log.read_text().splitlines()


def test_n2b_fremder_monitor_bleibt_an(tmp_path):
    c = _session(tmp_path, monitor_an=True, multiseat=False)
    assert "xrandr --output DVI-I-1-1 --mode 1080x1920 --pos 0x0 --primary" in c
    assert "xrandr --output HDMI-A-1 --off" not in c


@pytest.mark.parametrize("monitor_an, multiseat", [(False, False), (True, True)], ids=["ohne-monitor", "multiseat-an"])
def test_n2b_sonst_wie_bisher_abschalten(tmp_path, monitor_an, multiseat):
    assert "xrandr --output HDMI-A-1 --off" in _session(tmp_path, monitor_an=monitor_an, multiseat=multiseat)
