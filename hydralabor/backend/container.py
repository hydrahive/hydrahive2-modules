"""Labor-Container `hh-labor` (PLAN-L1.md Baustein 3).

Bewusst NICHT über `containers.lifecycle` des Kerns: der kennt nur br0/hhnat0 und nimmt das default-Profil, das auf
LXC-Hosts `security.privileged=true` trägt (Befund hydratest 30.10.). Das Labor startet ohne Profil, ausdrücklich
unprivilegiert, mit eigener Platte im Standard-Speicherpool und NIC am Labor-Netz.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from pathlib import Path

from . import incus, network

NAME = "hh-labor"
_FALLBACK = "24.04"
_VERSION = re.compile(r'^VERSION_ID="?(\d{2}\.\d{2})"?$', re.MULTILINE)
_POOL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,62}$")
_WAIT_TRIES = 60
_WAIT_STEP = 1.0


class LaborError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _int_in(v: object, lo: int, hi: int) -> bool:
    return isinstance(v, int) and not isinstance(v, bool) and lo <= v <= hi


@dataclass(frozen=True)
class Limits:
    cpu: int = 2
    ram_mb: int = 4096
    disk_gb: int = 20

    def __post_init__(self) -> None:
        if not (_int_in(self.cpu, 1, 64) and _int_in(self.ram_mb, 1024, 262144) and _int_in(self.disk_gb, 10, 2000)):
            raise LaborError("labor_limits_invalid")


def _ubuntu_version(path: Path = Path("/etc/os-release")) -> str:
    """Ubuntu-Version des Servers fürs Bild; sonst (Debian, unlesbar, komisch) 24.04."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return _FALLBACK
    m = _VERSION.search(text)
    return m.group(1) if m and "ID=ubuntu" in text.split() else _FALLBACK


async def exists() -> bool:
    rc, out, _ = await incus.run("list", "--format", "csv", "-c", "n")
    return rc == 0 and NAME in out.split()


async def _pool() -> str:
    rc, out, _ = await incus.run("profile", "device", "get", "default", "root", "pool")
    pool = out.strip()
    if rc != 0 or not _POOL.match(pool):
        raise LaborError("labor_no_storage_pool")
    return pool


async def launch(limits: Limits) -> None:
    if await exists():
        return
    pool = await _pool()
    args = ["launch", "--no-profiles", "-s", pool, "-n", network.NET,
            "-c", f"limits.cpu={limits.cpu}", "-c", f"limits.memory={limits.ram_mb}MiB",
            "-c", "security.privileged=false", "-c", "security.nesting=true",
            "-d", f"root,size={limits.disk_gb}GiB",
            "--", f"images:ubuntu/{_ubuntu_version()}", NAME]
    rc, _, _ = await incus.run(*args, timeout=600)
    if rc != 0:
        raise LaborError("labor_launch_failed")


async def wait_for_address() -> None:
    """Bis eth0 eine IPv4 hat (direkt nach dem Start: noch keine → DNS-Probe schlüge fälschlich fehl)."""
    for _ in range(_WAIT_TRIES):
        rc, _, _ = await incus.run("exec", NAME, "--", "bash", "-c", "ip -4 -o addr show eth0 | grep -q inet",
                                   timeout=20)
        if rc == 0:
            return
        await asyncio.sleep(_WAIT_STEP)
    raise LaborError("labor_no_address")


async def launch_and_probe(limits: Limits) -> dict:
    """Container anlegen und Sperre aus ihm heraus prüfen. Keine Adresse oder Netz offen → Container wieder weg."""
    await launch(limits)
    try:
        await wait_for_address()
        return await network.probe(NAME, await network.gateway())
    except (LaborError, network.LaborNetworkError):
        await remove()
        raise


async def stop() -> None:
    await incus.run("stop", NAME, "--force", timeout=120)


async def start() -> None:
    await incus.run("start", NAME, timeout=120)


async def remove() -> None:
    await incus.run("delete", NAME, "--force", timeout=120)
