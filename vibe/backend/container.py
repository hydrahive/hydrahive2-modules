"""Vibe-Container `hh-vibe-<projekt-id>` (PLAN-V1.md Baustein 2; Muster hydralabor/backend/container.py).

Bewusst NICHT über `containers.lifecycle` des Kerns: der kennt nur br0/hhnat0 und nimmt das default-Profil, das auf
LXC-Hosts `security.privileged=true` trägt (Befund hydratest 30.10.). Vibe startet ohne Profil, ausdrücklich
unprivilegiert, ohne Verschachtelung (Vibe baut Webseiten, keine Container), mit eigener Platte im Standard-Speicher-
pool und NIC am Vibe-Netz. Mehrere Container teilen sich das Netz; der Name kommt aus der Projekt-ID und wird geprüft.
Das Image ist fest (IMAGE_RELEASE), nicht die Ubuntu-Version des Servers.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass

from . import incus, network

PREFIX = network.PREFIX
# Festes, getestetes Image. NICHT die Server-Version: ein Container aus images:ubuntu/26.04 bekam in der echten Probe
# (5.11., incus 6.0.0, Ubuntu-26.04-Server) nie eine IPv4-Adresse, images:ubuntu/24.04 nach 1 s.
IMAGE_RELEASE = "24.04"
_POOL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,62}$")
_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,54}$")            # PREFIX (8) + 55 ≤ 63 Zeichen, K1: ^[a-z][a-z0-9-]{1,62}$
_NAME = re.compile(r"^hh-vibe-[a-z0-9][a-z0-9-]{0,54}$")
_WAIT_TRIES = 60
_WAIT_STEP = 1.0


class VibeError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def name_for(project_id: str) -> str:
    """Container-Name aus der Projekt-ID. Alles, was nicht klein/Ziffer/Bindestrich ist, wird abgelehnt (kein Zeichen
    kommt je in eine Shell, aber der Name steckt in incus-Aufrufen und in nginx-Dateinamen)."""
    if not isinstance(project_id, str) or not _ID.fullmatch(project_id):
        raise VibeError("vibe_name_invalid")
    return PREFIX + project_id


def is_vibe_name(name: str) -> bool:
    return isinstance(name, str) and _NAME.fullmatch(name) is not None


def _int_in(v: object, lo: int, hi: int) -> bool:
    return isinstance(v, int) and not isinstance(v, bool) and lo <= v <= hi


@dataclass(frozen=True)
class Limits:
    cpu: int = 2
    ram_mb: int = 2048
    disk_gb: int = 10

    def __post_init__(self) -> None:
        if not (_int_in(self.cpu, 1, 16) and _int_in(self.ram_mb, 512, 32768) and _int_in(self.disk_gb, 2, 200)):
            raise VibeError("vibe_limits_invalid")


async def exists(project_id: str) -> bool:
    name = name_for(project_id)
    rc, out, _ = await incus.run("list", "--format", "csv", "-c", "n")
    return rc == 0 and name in out.split()


async def _pool() -> str:
    rc, out, _ = await incus.run("profile", "device", "get", "default", "root", "pool")
    pool = out.strip()
    if rc != 0 or not _POOL.match(pool):
        raise VibeError("vibe_no_storage_pool")
    return pool


async def launch(project_id: str, limits: Limits) -> None:
    name = name_for(project_id)
    if await exists(project_id):
        return
    pool = await _pool()
    args = ["launch", "--no-profiles", "-s", pool, "-n", network.NET,
            "-c", f"limits.cpu={limits.cpu}", "-c", f"limits.memory={limits.ram_mb}MiB",
            "-c", "security.privileged=false", "-c", "security.nesting=false",
            "-d", f"root,size={limits.disk_gb}GiB",
            "--", f"images:ubuntu/{IMAGE_RELEASE}", name]
    rc, _, _ = await incus.run(*args, timeout=600)
    if rc != 0:
        raise VibeError("vibe_launch_failed")


async def wait_for_address(project_id: str) -> None:
    """Bis eth0 eine IPv4 hat (direkt nach dem Start: noch keine → DNS-Probe schlüge fälschlich fehl)."""
    name = name_for(project_id)
    for _ in range(_WAIT_TRIES):
        rc, _, _ = await incus.run("exec", name, "--", "bash", "-c", "ip -4 -o addr show eth0 | grep -q inet",
                                   timeout=20)
        if rc == 0:
            return
        await asyncio.sleep(_WAIT_STEP)
    raise VibeError("vibe_no_address")


async def launch_and_probe(project_id: str, limits: Limits) -> dict:
    """Container anlegen und Sperre aus ihm heraus prüfen. Keine Adresse oder Netz offen → Container wieder weg."""
    await launch(project_id, limits)
    try:
        await wait_for_address(project_id)
        return await network.probe(name_for(project_id), await network.gateway())
    except (VibeError, network.VibeNetworkError):
        await remove(project_id)
        raise


async def running(project_id: str) -> bool:
    name = name_for(project_id)
    rc, out, _ = await incus.run("list", "--format", "csv", "-c", "ns")
    return rc == 0 and any(line.split(",")[:2] == [name, "RUNNING"] for line in out.splitlines())


async def stop(project_id: str) -> None:
    await incus.run("stop", name_for(project_id), "--force", timeout=120)


async def start(project_id: str) -> None:
    await incus.run("start", name_for(project_id), timeout=120)


async def remove(project_id: str) -> None:
    await incus.run("delete", name_for(project_id), "--force", timeout=120)


async def all_names() -> set[str]:
    """Alle Container mit dem Vibe-Präfix (und nur die)."""
    rc, out, _ = await incus.run("list", "--format", "csv", "-c", "n")
    return {n for n in out.split() if is_vibe_name(n)} if rc == 0 else set()
