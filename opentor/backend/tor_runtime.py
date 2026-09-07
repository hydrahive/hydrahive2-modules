from __future__ import annotations

import os
import shutil
import socket
import subprocess
import time
from pathlib import Path


class TorRuntimeError(RuntimeError):
    pass


def _runtime_dir() -> Path:
    value = os.environ.get("HYDRAHIVE_OPENTOR_RUNTIME")
    if not value:
        raise TorRuntimeError("runtime_missing")
    return Path(value).resolve()


def _port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def _tor_binary() -> str:
    configured = os.environ.get("HYDRAHIVE_TOR_BIN")
    if configured and Path(configured).is_file():
        return configured
    found = shutil.which("tor")
    if found:
        return found
    candidate = _runtime_dir() / "tor" / "usr" / "bin" / "tor"
    if candidate.is_file():
        return str(candidate)
    raise TorRuntimeError("tor_binary_missing")


def ensure_tor() -> tuple[str, int, int]:
    host = os.environ.get("TOR_SOCKS_HOST", "127.0.0.1")
    socks_port = int(os.environ.get("TOR_SOCKS_PORT", "9050"))
    control_port = int(os.environ.get("TOR_CONTROL_PORT", "9051"))
    if _port_open(host, socks_port):
        return host, socks_port, control_port

    runtime = _runtime_dir()
    data_dir = runtime / "tor-data"
    data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    torrc = data_dir / "torrc"
    torrc.write_text(
        f"SocksPort {host}:{socks_port}\n"
        f"ControlPort {host}:{control_port}\n"
        f"DataDirectory {data_dir}\n"
        "CookieAuthentication 1\n"
        "SafeSocks 1\n"
        "AvoidDiskWrites 1\n",
        encoding="utf-8",
    )
    tor_bin = _tor_binary()
    log_path = runtime / "tor.log"
    runtime.mkdir(parents=True, exist_ok=True)
    log_file = log_path.open("ab")
    proc = subprocess.Popen(
        [tor_bin, "-f", str(torrc), "--RunAsDaemon", "0"],
        stdin=subprocess.DEVNULL,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        close_fds=True,
    )
    log_file.close()
    (runtime / "tor.pid").write_text(str(proc.pid), encoding="ascii")
    deadline = time.monotonic() + 35
    while time.monotonic() < deadline:
        if _port_open(host, socks_port):
            return host, socks_port, control_port
        if proc.poll() is not None:
            raise TorRuntimeError("tor_start_failed")
        time.sleep(0.5)
    raise TorRuntimeError("tor_start_timeout")
