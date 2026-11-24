"""Testumgebung für multiseat-apply.sh / multiseat-revert.sh: nachgebautes System unter tmp + Ersatzprogramme im PATH.

Die Ersatzprogramme (systemctl, systemd-run, loginctl, apt-get, pgrep, lightdm, sleep) ändern nichts am Rechner; sie
schreiben jeden Aufruf in calls.log. `loginctl attach/flush-devices` legen/entfernen eine 72-seat-Regel wie systemd.
Sitzungsliste für die Prüfung über die Datei sessions (Format von `loginctl list-sessions --no-legend`).
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from _seats_fixture import NV, build
from backend import seat_plan, seats, seats_snapshot

EXT = Path(__file__).resolve().parents[1] / "extension"
SESS_OK = "91 1003 hydrahive-kiosk seat0 53670 user tty5 no -\n92 115 lightdm seat1 53700 greeter - no -\n"
SESS_NO_SEAT1 = "91 1003 hydrahive-kiosk seat0 53670 user tty5 no -\n"
SESS_KIOSK_BOTH = SESS_OK + "93 1003 hydrahive-kiosk seat1 53800 user - no -\n"

_FAKE = r"""#!/bin/bash
echo "$(basename "$0") $*" >> "$HH_FAKE_LOG"
R="$HH_MULTISEAT_ROOT"
case "$(basename "$0") $1" in
  "loginctl attach") mkdir -p "$R/etc/udev/rules.d"; echo "$3" >> "$R/etc/udev/rules.d/72-seat-hh.rules"
    rm -f "$R/.udev-geladen" ;;                                # neue Regel: udev kennt sie erst nach --reload
  "loginctl flush-devices") rm -f "$R"/etc/udev/rules.d/72-seat-*.rules "$R/.udev-geladen" ;;
  "udevadm control") [ "$2" = "--reload" ] && touch "$R/.udev-geladen" ;;
  "udevadm info")   # Eigenschaften: udev.props des Geräts + ID_SEAT=seat1, solange das Gerät so markiert ist
    for a in "$@"; do case "$a" in --path=*) d="$R${a#--path=}" ;; esac; done
    [ -f "$d/uevent" ] || exit 1
    cat "$d/udev.props" 2>/dev/null; [ -f "$d/.seat1" ] && echo "ID_SEAT=seat1"; exit 0 ;;
  "udevadm trigger")   # wirkt nur mit geladenen Regeln; ohne --parent-match nur das Gerät selbst, nicht die Kinder
    [ -f "$R/.udev-geladen" ] || exit 0
    for a in "$@"; do case "$a" in --parent-match=*) t="${a#--parent-match=}"; deep=1 ;; /sys/*) t="$a"; deep=0 ;; esac; done
    if [ "$deep" = 1 ]; then list="$(find "$R$t" -name uevent -type f -printf '%h\n')"; else list="$R$t"; fi
    rules="$(cat "$R"/etc/udev/rules.d/72-seat-*.rules 2>/dev/null)"
    while IFS= read -r d; do
      [ -f "$d/uevent" ] || continue
      grep -q ':seat:' "$d/udev.props" 2>/dev/null || continue
      hit=0; while IFS= read -r r; do [ -n "$r" ] && case "${d#$R}/" in "$r"/*) hit=1 ;; esac; done <<<"$rules"
      if [ "$hit" = 1 ]; then touch "$d/.seat1"; else rm -f "$d/.seat1"; fi
    done <<<"$list" ;;
  "loginctl list-sessions")   # sessions.retry gilt ab dem 2. Neustart von sddm (Wiederholung im Rückbau)
    if [ -f "$HH_FAKE_SESSIONS.retry" ] && [ "$(grep -c '^systemctl restart sddm.service$' "$HH_FAKE_LOG")" -ge 2 ]; then
      cat "$HH_FAKE_SESSIONS.retry"; else cat "$HH_FAKE_SESSIONS" 2>/dev/null; fi ;;
  "loginctl list-seats")      # seat1 meldet sich noch so oft, wie in seat1.count steht (udev/logind langsam)
    echo "seat0"; c="$(cat "$HH_FAKE_SEAT1" 2>/dev/null || echo 0)"
    if [ "$c" -gt 0 ]; then echo "seat1"; echo $((c - 1)) > "$HH_FAKE_SEAT1"; fi ;;
  "pgrep "*) [ -f "$HH_FAKE_FIREFOX" ] ;;
  "apt-get "*) [ ! -f "$HH_FAKE_APT_FAIL" ] ;;
esac
"""
FAKES = ("systemctl", "systemd-run", "loginctl", "apt-get", "pgrep", "lightdm", "sleep", "udevadm")
SEAT1_MARK = ".seat1"
PLAIN = ("# vorher\n[Autologin]\nUser=hydrahive-kiosk\nSession=hydrahive-vitrine-kiosk\nRelogin=true\n")


def udev_tree(root: Path, attach: list[str]) -> dict[str, bool]:
    """udev-Geräte unter den attach-Pfaden (uevent + udev.props): Pfad → seat-getaggt. Kinder wie am Server 24.11.:
    Grafik → drm-Karte (seat) + Ausgang (ohne seat); USB-Empfänger → Schnittstelle (ohne), input/event/hidraw (seat)."""
    gpu, snd, usb = attach
    kids = {gpu: [("drm/cardX", True), ("drm/cardX/cardX-HDMI-A-1", False)],
            snd: [("controlC0", False)],
            usb: [("1-5:1.0", False), ("1-5:1.0/0003:24AE:1008.000B/input/input31", True),
                  ("1-5:1.0/0003:24AE:1008.000B/input/input31/event16", True),
                  ("1-5:1.0/0003:24AE:1008.000B/hidraw/hidraw0", True)]}
    out: dict[str, bool] = {}
    for p in attach:
        for rel, seat in [("", True), *kids[p]]:
            path = f"{p}/{rel}" if rel else p
            d = root / path.lstrip("/")
            d.mkdir(parents=True, exist_ok=True)
            (d / "uevent").write_text("")
            (d / "udev.props").write_text("TAGS=:seat:uaccess:\nCURRENT_TAGS=:seat:uaccess:\n" if seat else "TAGS=:power-switch:\n")
            out[path] = seat
    return out


def tills_plan(sys_root: Path) -> dict:
    """Plan aus Tills nachgestelltem Aufbau: NVIDIA + HDMI-Ton + Rapoo (USB 1-5) an seat1, Rest bei der Vitrine."""
    snap = seats_snapshot.read(sys_root)
    a = {d["id"]: "seat0" for k in ("gpus", "sound", "inputs") for d in snap[k]}
    a.update({f"gpu:pci:{NV}": "seat1", f"sound:pci:{NV[:-1]}1": "seat1", "input:usb:1-5": "seat1"})
    return seat_plan.build_plan(snap, seats.validate(snap, a))


class Env:
    def __init__(self, tmp: Path):
        self.tmp = tmp
        self.root = build(tmp / "root")
        self.bin = tmp / "bin"
        self.bin.mkdir()
        for name in FAKES:
            (self.bin / name).write_text(_FAKE)
            (self.bin / name).chmod(0o755)
        self.log = tmp / "calls.log"
        self.log.write_text("")
        self.sessions = tmp / "sessions"
        self.firefox = tmp / "firefox.on"
        self.apt_fail = tmp / "apt.fail"
        self.seat1 = tmp / "seat1.count"
        r = self.root
        # USB-Gerätebaum (Fixture kennt nur /proc), USB-Display-Gerät, EVDI-Ausgang an
        for p in tills_plan(r)["attach"]:
            (r / p.lstrip("/")).mkdir(parents=True, exist_ok=True)
        self.udev_devices = udev_tree(r, tills_plan(r)["attach"])
        (r / "dev/dri/by-path").mkdir(parents=True)
        (r / "dev/dri/card1").write_text("")
        (r / "dev/dri/by-path/platform-evdi.0-card").symlink_to("../card1")
        (r / "sys/class/drm/card1-DVI-I-1/enabled").write_text("enabled\n")
        # Ausgangslage wie bei Till: sddm aktiv unter /usr/bin, eigene sddm.conf vom Kiosk
        (r / "etc/X11").mkdir(parents=True)
        (r / "etc/X11/default-display-manager").write_text("/usr/bin/sddm\n")
        (r / "etc/sddm.conf").write_text(PLAIN)
        (r / "usr/lib/systemd/system").mkdir(parents=True)
        (r / "usr/lib/systemd/system/sddm.service").write_text("[Unit]\n")
        (r / "etc/systemd/system").mkdir(parents=True)
        (r / "etc/systemd/system/display-manager.service").symlink_to(r / "usr/lib/systemd/system/sddm.service")
        self.files = tmp / "in"
        self.files.mkdir()

    def write_plan(self, plan: dict | None = None) -> list[str]:
        plan = plan or tills_plan(self.root)
        (self.files / "plan.json").write_text(json.dumps(plan))
        (self.files / "lightdm.conf").write_text(seat_plan.render_lightdm(plan))
        (self.files / "xorg.conf").write_text(seat_plan.render_xorg(plan))
        return [str(self.files / n) for n in ("plan.json", "lightdm.conf", "xorg.conf")]

    def run(self, script: str, *args: str, sessions: str = SESS_OK, firefox: bool = True) -> subprocess.CompletedProcess:
        self.sessions.write_text(sessions)
        if firefox:
            self.firefox.write_text("1")
        elif self.firefox.exists():
            self.firefox.unlink()
        env = {**os.environ, "PATH": f"{self.bin}:{os.environ['PATH']}", "HH_MULTISEAT_ROOT": str(self.root),
               "HH_FAKE_LOG": str(self.log), "HH_FAKE_SESSIONS": str(self.sessions), "HH_FAKE_FIREFOX": str(self.firefox),
               "HH_FAKE_APT_FAIL": str(self.apt_fail), "HH_FAKE_SEAT1": str(self.seat1), "HH_MULTISEAT_CHECK_SECONDS": "3"}
        return subprocess.run(["bash", str(EXT / script), *args], env=env, capture_output=True, text=True, timeout=60,
                              check=False)

    def calls(self) -> list[str]:
        return self.log.read_text().splitlines()

    def etc(self, rel: str) -> Path:
        return self.root / "etc" / rel
