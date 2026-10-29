"""Sender steuern (PLAN-E2.md „Sendebetrieb“): Konfiguration schreiben, starten, stoppen, überspringen, Status.

root-Befehle laufen nur über _root() (`sudo -n bash`, Regel des Installers) und enthalten nur feste Texte – nie
etwas aus der Datenbank. Sendername u. Ä. stehen nur in den Konfigurationsdateien (0600, Besitzer hydrahive).
Der Merker sender.on sorgt dafür, dass der Sender nach einem Modul-Update wieder läuft (install.sh).
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import urllib.request
from pathlib import Path

from hydrahive.settings import settings

from . import feed_auth, listener_apply, service_files, station

UNITS = ("hydrahive-radiostream-icecast", "hydrahive-radiostream-liquidsoap")
WEB_DIR = Path("/var/www/hydrahive-radiostream")
SOCKET = Path("/run/hydrahive-radiostream/radio.sock")


def DATA_DIR() -> Path:  # noqa: N802 - in Tests ersetzbar
    return settings.data_dir / "radiostream"


def CONFIG_DIR() -> Path:  # noqa: N802 - in Tests ersetzbar
    return settings.config_dir / "radiostream"


class ControlError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _root(script: str) -> tuple[int, str]:
    cmd = ["bash", "-c", script] if os.getuid() == 0 else ["sudo", "-n", "bash", "-c", script]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    return r.returncode, (r.stdout + r.stderr).strip()


def _units_installed() -> bool:
    return all(Path(f"/etc/systemd/system/{u}.service").is_file() for u in UNITS)


def _write_private(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".neu")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(text)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def write_config() -> None:
    src_pw = feed_auth.read_secret("RADIOSTREAM_SOURCE_PASSWORD")
    admin_pw = feed_auth.read_secret("RADIOSTREAM_ADMIN_PASSWORD")
    key = feed_auth.read_secret("RADIOSTREAM_FEED_KEY")
    if not (src_pw and admin_pw and key):
        raise ControlError("radiostream_service_missing")
    st = station.get()
    data = DATA_DIR()
    pause = data / "pausenzeichen.mp3"
    _write_private(CONFIG_DIR() / "icecast.xml", service_files.icecast_xml(
        source_password=src_pw, admin_password=admin_pw, max_listeners=int(st["max_listeners"]), name=st["name"],
        log_dir=str(data / "log")))
    _write_private(data / "radio.liq", service_files.liquidsoap_script(
        feed_base=f"http://127.0.0.1:{settings.port}/api/modules/radiostream", feed_key=key, source_password=src_pw,
        name=st["name"], subtitle=st["subtitle"], fallback_file=str(pause) if pause.is_file() else "",
        control_socket=str(SOCKET), now_file=str(WEB_DIR / "jetzt.json")))


def start() -> None:
    if not _units_installed():
        raise ControlError("radiostream_service_missing")
    write_config()
    rc, _ = _root(f"systemctl enable --now {' '.join(UNITS)} && systemctl restart {' '.join(UNITS)}")
    if rc != 0:
        raise ControlError("radiostream_service_failed")
    (DATA_DIR() / "sender.on").touch()
    apply_listener_site()


def stop() -> None:
    (DATA_DIR() / "sender.on").unlink(missing_ok=True)
    _root(f"systemctl disable --now {' '.join(reversed(UNITS))}")
    listener_apply.remove(_root, DATA_DIR())


def _port_taken_by_other(port: int) -> bool:
    return listener_apply.port_taken_by_other(port, _root)


def apply_listener_site() -> None:
    st = station.get()
    if st["reach"] == "off":
        listener_apply.remove(_root, DATA_DIR())
        return
    if _port_taken_by_other(int(st["listen_port"])):
        raise ControlError("radiostream_port_in_use")
    if not listener_apply.apply(st, root=_root, data_dir=DATA_DIR(), web_dir=WEB_DIR, write=_write_public):
        raise ControlError("radiostream_nginx_failed")


def _write_public(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".neu")
    tmp.write_text(text)
    os.chmod(tmp, 0o644)
    os.replace(tmp, path)


def _active(unit: str) -> bool:
    rc, _ = _root(f"systemctl is-active --quiet {unit}")
    return rc == 0


def status() -> dict:
    return {"installed": _units_installed(), "running": all(_active(u) for u in UNITS)}


def _send(cmd: str) -> str:
    with socket.socket(socket.AF_UNIX) as s:
        s.settimeout(5)
        s.connect(str(SOCKET))
        s.sendall(f"{cmd}\nquit\n".encode())
        return s.recv(4096).decode(errors="replace")


def skip() -> None:
    if not status()["running"]:
        raise ControlError("radiostream_not_running")
    try:
        _send("sender.skip")
    except OSError:
        raise ControlError("radiostream_service_failed") from None


def now_playing() -> dict:
    try:
        d = json.loads((WEB_DIR / "jetzt.json").read_text())
    except (OSError, ValueError):
        d = None
    if not isinstance(d, dict):
        return {"artist": "", "title": ""}
    return {k: v if isinstance(v := d.get(k), str) else "" for k in ("artist", "title")}


def _icecast_status() -> dict | None:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{service_files.ICECAST_PORT}/status-json.xsl", timeout=3) as r:
            return json.loads(r.read())
    except (OSError, ValueError):
        return None


def listeners() -> int:
    src = ((_icecast_status() or {}).get("icestats") or {}).get("source")
    items = src if isinstance(src, list) else [src] if isinstance(src, dict) else []
    return sum(int(s.get("listeners") or 0) for s in items if isinstance(s, dict))
