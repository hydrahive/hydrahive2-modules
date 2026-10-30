"""Voraussetzungen (Assistent Schritt 1): incus da und ≥ 6.0, Platz für den Container + 10 GB Puffer im Speicherpool,
freier Arbeitsspeicher ≥ Grenze des Containers, Kern mit K1 (Projekt-Ausführung im Container).

Jede Prüfung liefert {id, ok, code, have, need}; die Oberfläche übersetzt `code`.
"""
from __future__ import annotations

import re
from pathlib import Path

from . import incus

SPARE_GB = 10
_VER = re.compile(r"^Server version:\s*(\S+)", re.MULTILINE)
_NUM = re.compile(r'(space used|total space):\s*"?(\d+)"?')


def _mem_available_mb(path: Path = Path("/proc/meminfo")) -> int | None:
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) // 1024
    except (OSError, ValueError, IndexError):
        return None
    return None


def _core_has_k1() -> bool:
    try:
        from hydrahive.agents import _managed  # noqa: F401
        from hydrahive.projects import execution  # noqa: F401
        from hydrahive.runner._project_tool_scope import CONTAINER_ALLOWED  # noqa: F401
    except ImportError:
        return False
    return True


async def _incus_version() -> str:
    rc, out, _ = await incus.run("version")
    m = _VER.search(out)
    return m.group(1) if rc == 0 and m else ""


async def _pool_free_gb() -> int | None:
    rc, pool, _ = await incus.run("profile", "device", "get", "default", "root", "pool")
    if rc != 0 or not pool.strip():
        return None
    rc, out, _ = await incus.run("storage", "info", pool.strip(), "--bytes")
    vals = dict(_NUM.findall(out))
    if rc != 0 or "space used" not in vals or "total space" not in vals:
        return None
    return (int(vals["total space"]) - int(vals["space used"])) // 1024**3


def _version_ok(v: str) -> bool:
    try:
        return tuple(int(x) for x in v.split(".")[:2]) >= (6, 0)
    except ValueError:
        return False


def _c(cid: str, ok: bool, code: str, have=None, need=None) -> dict:
    return {"id": cid, "ok": ok, "code": "" if ok else code, "have": have, "need": need}


async def run(*, disk_gb: int, ram_mb: int) -> dict:
    if not incus.available():
        res = [_c("incus", False, "labor_incus_missing")]
    else:
        ver = await _incus_version()
        free = await _pool_free_gb()
        mem = _mem_available_mb()
        need_disk = disk_gb + SPARE_GB
        res = [_c("incus", True, ""),
               _c("incus_version", _version_ok(ver), "labor_incus_too_old", ver, "6.0"),
               _c("storage", free is not None and free >= need_disk, "labor_storage_low", free, need_disk),
               _c("memory", mem is not None and mem >= ram_mb, "labor_memory_low", mem, ram_mb)]
    res.append(_c("core", _core_has_k1(), "labor_core_too_old"))
    return {"ok": all(c["ok"] for c in res), "checks": res}
