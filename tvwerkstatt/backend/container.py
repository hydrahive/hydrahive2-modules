"""Der eine Bau-Container `hh-tvwerkstatt` (PLAN-E1.md Baustein 3; Muster vibe/backend/container.py).

Ohne Profil, ausdrücklich unprivilegiert, ohne Verschachtelung, eigene ID-Zuordnung, Platte im Standard-Speicherpool,
Netzkarte nur am eigenen Netz `hhtvw0` (Sperrliste). Festes Image, nicht die Ubuntu-Version des Servers.
"""
from __future__ import annotations

import asyncio
import json
import re

from hydrahive.containers.incus_client import IncusError

from . import incus, network

NAME = "hh-tvwerkstatt"
IMAGE = "images:ubuntu/24.04"         # 26.04 bekam bei vibe keine IPv4 (Probe 5.11.)
CPU = 4
RAM_MB = 4096
DISK_GB = 12                          # Probelauf: 1,2 GB im Heimordner, System + Werkzeuge ca. 3 GB
_POOL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,62}$")
_WAIT_TRIES = 60
_WAIT_STEP = 1.0


class TvwContainerError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


async def _run(*args: str, timeout: float = 120) -> tuple[int, str]:
    try:
        rc, out, _ = await incus.run(*args, timeout=timeout)
    except IncusError:
        return 1, ""
    return rc, out


async def status() -> str:
    """missing | stopped | running | unknown (Liste nicht lesbar)."""
    rc, out = await _run("list", "--format", "json")
    if rc != 0:
        return "unknown"
    try:
        items = json.loads(out or "[]")
    except ValueError:
        return "unknown"
    for item in items:
        if item.get("name") == NAME:
            return "running" if item.get("status") == "Running" else "stopped"
    return "missing"


async def _pool() -> str:
    rc, out = await _run("profile", "device", "get", "default", "root", "pool")
    pool = out.strip()
    if rc != 0 or not _POOL.match(pool):
        raise TvwContainerError("tvw_no_storage_pool")
    return pool


async def ensure_running() -> None:
    """Anlegen, wenn er fehlt; starten, wenn er steht. Danach läuft er (oder es gibt einen Fehlercode)."""
    now = await status()
    if now == "unknown":
        raise TvwContainerError("tvw_container_down")
    if now == "missing":
        rc, _ = await _run("launch", "--no-profiles", "-s", await _pool(), "-n", network.NET,
                           "-c", f"limits.cpu={CPU}", "-c", f"limits.memory={RAM_MB}MiB",
                           "-c", "security.privileged=false", "-c", "security.nesting=false",
                           "-c", "security.idmap.isolated=true", "-d", f"root,size={DISK_GB}GiB",
                           "--", IMAGE, NAME, timeout=600)
        if rc != 0:
            raise TvwContainerError("tvw_launch_failed")
    elif now == "stopped":
        await _run("start", NAME)
    if await status() != "running":
        raise TvwContainerError("tvw_container_down")


async def wait_for_address() -> None:
    """Bis eth0 eine IPv4 hat – sonst schlüge die Netzprobe fälschlich fehl."""
    for _ in range(_WAIT_TRIES):
        rc, _ = await _run("exec", NAME, "--", "bash", "-c", "ip -4 -o addr show eth0 | grep -q inet", timeout=20)
        if rc == 0:
            return
        await asyncio.sleep(_WAIT_STEP)
    raise TvwContainerError("tvw_no_address")


async def stop() -> None:
    if await status() != "running":
        return
    await _run("stop", NAME, "--force")
    if await status() == "running":
        raise TvwContainerError("tvw_container_down")


async def remove() -> None:
    """Container weg, danach Netz und Sperrliste, wenn sonst nichts daran hängt."""
    if await status() not in ("missing",):
        await _run("delete", NAME, "--force")
        if await status() != "missing":
            raise TvwContainerError("tvw_container_remove_failed")
    await network.remove_if_unused()
