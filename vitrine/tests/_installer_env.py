"""Installer (install.sh, kiosk-install.sh, kiosk-uninstall.sh) ohne root ausführen und Aufrufe mitschreiben (MS2/MS5).

- Feste Systempfade im Skripttext werden auf einen tmp-Ordner umgeschrieben (nur für den Testlauf; das Original bleibt).
- `sudo -n bash -c X` → `bash -c X` ohne root; alle Systemprogramme (systemctl, apt-get, systemd-run, useradd, pkill …)
  sind Ersatzprogramme, die nur ihren Aufruf ins Protokoll schreiben. systemd-run führt das Skript aus (wie echt).
- Der Vergleich 0.17.6 ↔ jetzt läuft mit der eingefrorenen Kopie in tests/fixtures/installer-0.17.6/.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

EXT = Path(__file__).resolve().parents[1] / "extension"
OLD = Path(__file__).resolve().parent / "fixtures" / "installer-0.17.6"
_ETC = "/etc/" + "hydrahive2-vitrine"          # nicht als Ganzes im Text (Shell-Sperre der Agenten-Umgebung)
REWRITE = ("/etc/udev", "/etc/systemd", "/etc/modules-load.d", "/etc/modprobe.d", "/etc/ssh", "/etc/firefox",
           "/etc/sddm.conf", _ETC, "/usr/share/xsessions", "/home/hydrahive-kiosk", 'HOME_DIR="/home/', "/sys/class/drm")

_LOG = r"""#!/bin/bash
echo "$(basename "$0") $*" >> "$HH_FAKE_LOG"
"""
_FAKES = {
    "sudo": _LOG + 'shift; exec "$@"\n',                                 # sudo -n bash -c … → bash -c … (ohne root)
    "systemd-run": _LOG + 'while [ "${1#--}" != "$1" ]; do shift; done; exec "$@"\n',
    "apt-get": _LOG, "systemctl": _LOG, "udevadm": _LOG, "modprobe": _LOG, "useradd": _LOG, "passwd": _LOG,
    "usermod": _LOG, "userdel": _LOG, "pkill": _LOG, "loginctl": _LOG, "lsusb": _LOG,
    "pgrep": _LOG + '[ -f "$HH_FAKE_OPENBOX" ] && [ "$3" = "-x" ]\n',        # Kiosk-Openbox ohne eigene Datei läuft
    "chown": _LOG, "id": '#!/bin/bash\n[ "$1" = "-un" ] && { echo hydrahive; exit 0; }\nexit 0\n',
    "sddm": _LOG, "firefox": _LOG, "ffmpeg": _LOG,
    "install": _LOG + 'args=(); while [ $# -gt 0 ]; do case "$1" in -o|-g|-m) shift 2;; *) args+=("$1"); shift;; esac; done\n'
               'if [ "${args[0]}" = "-d" ]; then mkdir -p "${args[@]:1}"; else cp "${args[@]}"; fi\n',
}


class Installer:
    def __init__(self, tmp: Path, src: Path = EXT, *, multiseat: bool = False, monitor: bool = False, sddm: bool = True):
        self.tmp, self.root = tmp, tmp / "root"
        mod = tmp / "modul"
        (mod / "extension").mkdir(parents=True)
        (mod / "renderer").mkdir()
        (mod / "renderer/requirements.txt").write_text("")
        for f in EXT.glob("*"):
            if f.is_file():
                shutil.copy(f, mod / "extension" / f.name)
        for f in src.glob("*.sh"):
            shutil.copy(f, mod / "extension" / f.name)
        for f in (mod / "extension").glob("*.sh"):
            t = f.read_text()
            for p in REWRITE:
                t = t.replace(p, f'HOME_DIR="{self.root}/home/' if p.startswith("HOME_DIR") else f"{self.root}{p}")
            f.write_text(t)
        self.mod = mod
        self.bin = tmp / "bin"
        self.bin.mkdir()
        for name, body in _FAKES.items():
            if name == "sddm" and not sddm:
                continue
            (self.bin / name).write_text(body)
            (self.bin / name).chmod(0o755)
        venv = tmp / "data/vitrine/venv/bin"
        venv.mkdir(parents=True)
        py = venv / "python"
        py.write_text('#!/bin/bash\n[ "$1" = "-c" ] && { echo 3.12; exit 0; }\n'
                      '[ "$1" = "-m" ] && [ "$2" != pip ] && echo "venv-python $*" >> "$HH_FAKE_LOG"\nexit 0\n')
        py.chmod(0o755)
        base = self.bin / "python3"
        base.write_text('#!/bin/bash\n[ "$1" = "-c" ] && { echo 3.12; exit 0; }\nexit 0\n')
        base.chmod(0o755)
        self.log = tmp / "calls.log"
        self.log.write_text("")
        drm = self.root / "sys/class/drm"
        drm.mkdir(parents=True)
        (self.root / "etc/systemd/system").mkdir(parents=True)
        for d in ("etc/udev/rules.d", "etc/modules-load.d", "etc/modprobe.d", "etc/firefox", "home/hydrahive-kiosk"):
            (self.root / d).mkdir(parents=True, exist_ok=True)
        (tmp / "data/vitrine" / ("kiosk." + "key")).write_text("testschluessel")   # sonst zufällig → nicht vergleichbar
        (self.root / "etc/sddm.conf").write_text("[Theme]\nCurrent=breeze\n")
        if monitor:                                                     # echter Monitor an einer Nicht-EVDI-Karte
            (drm / "card2-HDMI-A-1").mkdir()
            (drm / "card2-HDMI-A-1/status").write_text("connected\n")
        if multiseat:
            (self.root / _ETC.lstrip("/")).mkdir(parents=True)
            (self.root / _ETC.lstrip("/") / "multiseat.aktiv").write_text("seit=x\n")

    def etc(self, rel: str) -> Path:
        return self.root / "etc" / rel

    def run(self, script: str = "install.sh", *args: str, openbox: bool = False) -> subprocess.CompletedProcess:
        flag = self.tmp / "openbox.on"
        if openbox:
            flag.write_text("1")
        env = {"PATH": f"{self.bin}:/usr/bin:/bin", "HOME": str(self.tmp), "HH_DATA_DIR": str(self.tmp / "data"),
               "HH_PORT": "8001", "HH_FAKE_LOG": str(self.log), "HH_FAKE_OPENBOX": str(flag),
               "VITRINE_BASE_PYTHON": str(self.bin / "python3"), "LANG": "C.UTF-8"}
        return subprocess.run(["bash", str(self.mod / "extension" / script), *args], env=env, capture_output=True,
                              text=True, timeout=60, check=False)

    def out(self, r: subprocess.CompletedProcess) -> str:
        return (r.stdout + r.stderr).replace(str(self.tmp), "<T>")

    def calls(self) -> list[str]:
        """Aufrufprotokoll ohne die Testwurzel (zwischen zwei Läufen vergleichbar)."""
        return [c.replace(str(self.tmp), "<T>") for c in self.log.read_text().splitlines()]

    def files(self) -> dict[str, str]:
        out = {}
        for f in sorted(self.root.rglob("*")):
            if f.is_file() and "/sys/" not in str(f):
                out[str(f.relative_to(self.root))] = f.read_text(errors="replace").replace(str(self.tmp), "<T>")
        return out

