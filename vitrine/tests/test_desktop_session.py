"""Multiseat: Standard-Desktop für seat1 aus dem System (lightdm user-session), live 24.11.2026.

Fehler am Server: ohne user-session bot lightdm „Default Xsession“ (lightdm-xsession.desktop, Exec=default) an.
Nachgestellte xsessions-Ordner; nichts liest das echte System.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from _seats_fixture import NV, build

from backend import desktop_session, seat_plan, seats, seats_snapshot

DESK = {
    "Lubuntu": "[Desktop Entry]\nName=Lubuntu\nExec=/usr/bin/startlxqt\nDesktopNames=LXQt\n",
    "lxqt": "[Desktop Entry]\nName=LXQt Desktop\nName[de]=LXQt-Arbeitsfläche\nExec=startlxqt\nDesktopNames=LXQt\n",
    "openbox": "[Desktop Entry]\nName=Openbox\nExec=/usr/bin/openbox-session\n",
    "lightdm-xsession": "[Desktop Entry]\nName=Default Xsession\nExec=default\n",
    "hydrahive-vitrine-kiosk": "[Desktop Entry]\nName=HydraHive Vitrine-Kiosk\nExec=/etc/x/kiosk-session.sh\n",
    "ubuntu": "[Desktop Entry]\nName=Ubuntu\nExec=env GNOME_SHELL_SESSION_MODE=ubuntu /usr/bin/gnome-session --session=ubuntu\n",
    "gnome": "[Desktop Entry]\nName=GNOME\nExec=/usr/bin/gnome-session\n",
    "versteckt": "[Desktop Entry]\nName=Alt\nExec=/usr/bin/startlxqt\nNoDisplay=true\n",
    "weg": "[Desktop Entry]\nName=Weg\nExec=/usr/bin/startlxqt\nHidden=true\n",
}


def _sys(root: Path, sessions: list[str], *, xsm: str | None = None, xdg: list[str] = ()) -> Path:
    xs = root / "usr/share/xsessions"
    xs.mkdir(parents=True, exist_ok=True)
    for name in sessions:
        (xs / f"{name}.desktop").write_text(DESK[name])
    bin_ = root / "usr/bin"
    bin_.mkdir(parents=True, exist_ok=True)
    for prog in ("startlxqt", "openbox-session", "gnome-session"):
        (bin_ / prog).write_text("#!/bin/sh\n")
    if xsm:                                              # wie Debian: /etc/alternatives/x-session-manager → /usr/bin/…
        alt = root / "etc/alternatives"
        alt.mkdir(parents=True, exist_ok=True)
        (alt / "x-session-manager").symlink_to(xsm)
        (root / "usr/bin/x-session-manager").symlink_to("/etc/alternatives/x-session-manager")
    for name in xdg:
        (root / f"etc/xdg/xdg-{name}").mkdir(parents=True)
    return root


def test_till_lubuntu_und_lxqt_beide_startlxqt(tmp_path):
    """Server 24.11.: Lubuntu und lxqt starten beide startlxqt; /etc/xdg/xdg-Lubuntu gibt den Ausschlag."""
    root = _sys(tmp_path, ["Lubuntu", "hydrahive-vitrine-kiosk", "lightdm-xsession", "lxqt", "openbox"],
                xsm="/usr/bin/startlxqt", xdg=["Lubuntu"])
    r = desktop_session.find(root)
    assert r["name"] == "Lubuntu" and r["reason"] == "x-session-manager+xdg"
    assert r["candidates"] == ["Lubuntu", "lxqt"]                    # Kiosk, Platzhalter, reiner WM nicht dabei


def test_beide_passen_ohne_xdg_alphabetisch(tmp_path):
    root = _sys(tmp_path, ["lxqt", "Lubuntu"], xsm="/usr/bin/startlxqt")
    r = desktop_session.find(root)
    assert r["name"] == "Lubuntu" and r["reason"] == "x-session-manager+alphabetisch"


def test_nur_gnome(tmp_path):
    root = _sys(tmp_path, ["ubuntu", "lightdm-xsession"], xsm="/usr/bin/gnome-session")
    r = desktop_session.find(root)
    assert r["name"] == "ubuntu" and r["reason"] == "x-session-manager"    # env … /usr/bin/gnome-session erkannt


def test_einzige_sitzung_ohne_alternative(tmp_path):
    root = _sys(tmp_path, ["gnome", "hydrahive-vitrine-kiosk"])
    assert desktop_session.find(root) == {"name": "gnome", "reason": "only_desktop", "candidates": ["gnome"]}


def test_nichts_passendes_mehrdeutig(tmp_path):
    root = _sys(tmp_path, ["gnome", "lxqt"], xsm="/usr/bin/openbox-session")
    r = desktop_session.find(root)
    assert r["name"] is None and r["reason"] == "ambiguous"


@pytest.mark.parametrize("sessions", [["hydrahive-vitrine-kiosk"], ["hydrahive-vitrine-kiosk", "lightdm-xsession"],
                                      ["versteckt", "weg"], []], ids=["kiosk", "kiosk+default", "versteckt", "leer"])
def test_kein_desktop(tmp_path, sessions):
    r = desktop_session.find(_sys(tmp_path, sessions, xsm="/usr/bin/startlxqt"))
    assert r["name"] is None and r["reason"] == "no_desktop"


def test_reiner_wm_nur_als_letzter_ausweg(tmp_path):
    r = desktop_session.find(_sys(tmp_path, ["openbox", "hydrahive-vitrine-kiosk"]))
    assert r["name"] == "openbox" and r["reason"] == "only_wm"
    r = desktop_session.find(_sys(tmp_path / "b", ["openbox", "lxqt"], xsm="/usr/bin/openbox-session"))
    assert r["name"] == "lxqt"                                         # Desktop vor WM, auch wenn die Alternative passt


def test_ungueltiger_name_wird_ignoriert(tmp_path):
    root = _sys(tmp_path, ["Lubuntu"], xsm="/usr/bin/startlxqt", xdg=["Lubuntu"])
    (root / "usr/share/xsessions/bö se;x.desktop").write_text(DESK["Lubuntu"])
    assert desktop_session.find(root)["name"] == "Lubuntu"


# --- Plan und lightdm-Datei --------------------------------------------------------------------------------------

def _plan(tmp_path: Path, **kw) -> dict:
    root = build(tmp_path)
    if kw:
        _sys(root, **kw)
    snap = seats_snapshot.read(root)
    a = {d["id"]: "seat0" for k in ("gpus", "sound", "inputs") for d in snap[k]}
    a.update({f"gpu:pci:{NV}": "seat1", f"sound:pci:{NV[:-1]}1": "seat1", "input:usb:1-5": "seat1"})
    return seat_plan.build_plan(snap, seats.validate(snap, a))


def test_lightdm_till_fall(tmp_path):
    p = _plan(tmp_path, sessions=["Lubuntu", "hydrahive-vitrine-kiosk", "lightdm-xsession", "lxqt", "openbox"],
              xsm="/usr/bin/startlxqt", xdg=["Lubuntu"])
    assert p["user_session"] == "Lubuntu" and p["user_session_reason"] == "x-session-manager+xdg"
    assert seat_plan.render_lightdm(p) == (
        "# Von HydraHive Vitrine geschrieben (Zweiter Arbeitsplatz). Rückbau: multiseat-revert.sh\n"
        "[Seat:seat0]\nautologin-user=hydrahive-kiosk\nautologin-session=hydrahive-vitrine-kiosk\n"
        "autologin-user-timeout=0\n\n[Seat:seat1]\ngreeter-session=lightdm-gtk-greeter\nuser-session=Lubuntu\n")


def test_lightdm_ohne_eindeutigen_desktop_wie_bisher(tmp_path):
    p = _plan(tmp_path, sessions=["hydrahive-vitrine-kiosk", "lightdm-xsession"])
    assert p["user_session"] is None and p["user_session_reason"] == "no_desktop"
    text = seat_plan.render_lightdm(p)
    assert "user-session" not in text and text.endswith("[Seat:seat1]\ngreeter-session=lightdm-gtk-greeter\n")
    assert "user-session" not in text.split("[Seat:seat1]")[0]          # seat0 bleibt Kiosk


@pytest.mark.parametrize("bad", ["Lu buntu", "x\nautologin-user=root", "../x", "a;b", ""])
def test_render_lehnt_ungueltigen_namen_ab(tmp_path, bad):
    p = {**_plan(tmp_path), "user_session": bad}
    text = seat_plan.render_lightdm(p)
    assert "user-session" not in text and text.count("autologin-user=") == 1


def test_nur_lesen_kein_schreiben_in_nutzerdaten():
    """Nur lesen: kein Schreiben, keine Nutzer-Homes, kein AccountsService (Code ohne Docstring/Kommentare)."""
    src = (Path(__file__).resolve().parents[1] / "backend" / "desktop_session.py").read_text()
    code = "\n".join(ln.split("#")[0] for ln in src.split('"""', 2)[2].splitlines())
    for bad in ("write", "open(", "unlink", "mkdir", "/home", "/var/lib/AccountsService", ".dmrc", "rename"):
        assert bad not in code, bad
    assert os.sep == "/"
