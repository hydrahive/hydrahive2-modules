"""Disk repair via ntfsfix / fsck — async streaming job."""
from __future__ import annotations

import asyncio
import logging
import re
import shlex
from dataclasses import dataclass, field
from typing import Optional

from .drives import _sudo_host, _DEVICE_RE, unmount_drive

logger = logging.getLogger(__name__)

_MAX_LINES = 500

_repairs: dict[str, "RepairJob"] = {}


@dataclass
class RepairJob:
    device: str                          # z.B. /dev/sdb1
    tool: str                            # "ntfsfix" | "fsck"
    status: str = "running"              # running | done | failed
    lines: list[str] = field(default_factory=list)


def start_repair(device: str, tool: str) -> RepairJob:
    """Startet einen Reparatur-Job für device.

    Läuft max. einmal gleichzeitig je Device — laufender Job wird ersetzt.
    """
    if not _DEVICE_RE.match(device):
        raise ValueError(f"Ungültiges Device: {device!r}")
    if tool not in ("ntfsfix", "fsck"):
        raise ValueError(f"Unbekanntes Werkzeug: {tool!r}")

    job = RepairJob(device=device, tool=tool)
    _repairs[device] = job
    asyncio.create_task(_run(job))
    return job


def get_repair(device: str) -> Optional[RepairJob]:
    return _repairs.get(device)


async def _run(job: RepairJob) -> None:
    device = job.device

    if job.tool == "ntfsfix":
        await _run_tool(job, ["ntfsfix", device])
    else:
        # fsck: zuerst unmounten (fsck auf gemountetes Dateisystem ist gefährlich)
        try:
            from .drives import list_drives
            drives = list_drives()
            mounted = next((d for d in drives if d.device == device and d.mountpoint), None)
            if mounted:
                job.lines.append(f"[archiver] aushängen: {mounted.mountpoint}")
                try:
                    unmount_drive(mounted.mountpoint)
                    job.lines.append("[archiver] ausgehängt")
                except RuntimeError as exc:
                    job.lines.append(f"[archiver] umount fehlgeschlagen: {exc}")
        except Exception as exc:
            job.lines.append(f"[archiver] drive-lookup fehlgeschlagen: {exc}")

        # fsck.ext4 -y -C 0  (auto-yes + Fortschritts-Kanal 0)
        await _run_tool(job, ["fsck.ext4", "-y", "-C", "0", device])


async def _run_tool(job: RepairJob, cmd_args: list[str]) -> None:
    logger.info("repair %s: %s", job.device, " ".join(cmd_args))
    full_cmd = _sudo_host(cmd_args)

    try:
        proc = await asyncio.create_subprocess_exec(
            *full_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
    except Exception as exc:
        logger.error("repair %s: start fehlgeschlagen: %s", job.device, exc)
        job.lines.append(f"[Fehler] {exc}")
        job.status = "failed"
        return

    assert proc.stdout
    buf = ""
    while True:
        chunk = await proc.stdout.read(4096)
        if not chunk:
            break
        buf += chunk.decode("utf-8", errors="replace")
        segments = re.split(r"[\r\n]", buf)
        buf = segments.pop()
        for seg in segments:
            seg = seg.strip()
            if seg:
                job.lines.append(seg)
                if len(job.lines) > _MAX_LINES:
                    job.lines = job.lines[-_MAX_LINES:]

    if buf.strip():
        job.lines.append(buf.strip())

    await proc.wait()
    rc = proc.returncode
    logger.info("repair %s: beendet rc=%d", job.device, rc)
    # fsck.ext4: rc=1 = Fehler behoben (Erfolg), rc=2 = Neustart empfohlen (ok)
    job.status = "done" if rc in (0, 1, 2) else "failed"
