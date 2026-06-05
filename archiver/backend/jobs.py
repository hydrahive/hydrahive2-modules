"""rsync job manager — startet Jobs, trackt Fortschritt, scannt nach Wallets."""
from __future__ import annotations

import asyncio
import logging
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# rsync --progress liefert (xfr#N, ir-chk=M/T) oder (xfr#N, to-chk=M/T)
_XFR_RE = re.compile(r"\(xfr#(\d+),\s*(?:ir|to)-chk=(\d+)/(\d+)\)")
_SPEED_RE = re.compile(r"[\d,\.]+\s+\d+%\s+(\S+/s)")

_WALLET_PATTERNS = [
    ("Bitcoin Core",      "wallet.dat"),
    ("Monero",            "*.keys"),
    ("Electrum",          "*.wallet"),
    ("Ethereum Keystore", "UTC--*"),
    ("Generic Key",       "*.key"),
    ("Private Key PEM",   "*.pem"),
]

_jobs: dict[int, "Job"] = {}


@dataclass
class Job:
    id: int
    user: str
    drive_path: str
    drive_label: str
    project_id: str
    folder_name: str
    target_path: str
    status: str = "running"
    pct: int = 0
    files_done: int = 0
    files_total: int = 0
    speed: str = ""
    error_count: int = 0
    errors: list[str] = field(default_factory=list)
    process: Optional[asyncio.subprocess.Process] = field(default=None, repr=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "drive_label": self.drive_label,
            "project_id": self.project_id,
            "folder_name": self.folder_name,
            "target_path": self.target_path,
            "status": self.status,
            "pct": self.pct,
            "files_done": self.files_done,
            "files_total": self.files_total,
            "speed": self.speed,
            "error_count": self.error_count,
            "errors": self.errors[-10:],
        }


def get_job(job_id: int) -> Optional[Job]:
    return _jobs.get(job_id)


def get_all_jobs() -> list[Job]:
    return list(_jobs.values())


def start_job(job: Job) -> None:
    _jobs[job.id] = job
    asyncio.create_task(_run(job))


def cancel_job(job_id: int) -> bool:
    job = _jobs.get(job_id)
    if not job or job.status != "running":
        return False
    if job.process:
        job.process.terminate()
    job.status = "cancelled"
    return True


async def _run(job: Job) -> None:
    target = Path(job.target_path)
    target.mkdir(parents=True, exist_ok=True)

    logger.info("archiver job %d: rsync %s → %s", job.id, job.drive_path, job.target_path)

    # stdbuf -o0: verhindert Output-Buffering von rsync in Pipe-Umgebung
    cmd = ["rsync", "-av", "--progress", "--ignore-errors",
           f"{job.drive_path}/", f"{job.target_path}/"]
    if shutil.which("stdbuf"):
        cmd = ["stdbuf", "-o0"] + cmd

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
    except Exception as exc:
        logger.error("archiver job %d: rsync start fehlgeschlagen: %s", job.id, exc)
        job.status = "failed"
        job.errors.append(str(exc))
        return

    job.process = proc

    assert proc.stdout
    buf = ""
    while True:
        # Chunk lesen statt readline — verarbeitet auch \r-getrennte Fortschrittszeilen
        chunk = await proc.stdout.read(4096)
        if not chunk:
            break
        buf += chunk.decode("utf-8", errors="replace")
        # Split nach \r und \n
        segments = re.split(r"[\r\n]", buf)
        # Letztes Segment ist ggf. unvollständig → zurückbehalten
        buf = segments.pop()
        for seg in segments:
            seg = seg.strip()
            if seg:
                _parse_line(job, seg)

    # Rest-Buffer verarbeiten
    if buf.strip():
        _parse_line(job, buf.strip())

    await proc.wait()
    rc = proc.returncode
    logger.info("archiver job %d: rsync beendet (rc=%d, %d/%d Dateien)", job.id, rc, job.files_done, job.files_total)
    job.status = "done" if rc in (0, 23, 24) else "failed"
    if job.files_total > 0:
        job.pct = 100


def _parse_line(job: Job, line: str) -> None:
    m = _XFR_RE.search(line)
    if m:
        job.files_done = int(m.group(1))
        remaining = int(m.group(2))
        total = int(m.group(3))
        job.files_total = total
        if total > 0:
            job.pct = min(99, int((total - remaining) / total * 100))

    s = _SPEED_RE.search(line)
    if s:
        job.speed = s.group(1)

    lower = line.lower()
    if ("failed" in lower or "error" in lower) and "rsync error" not in lower:
        job.error_count += 1
        job.errors.append(line.rstrip())


def scan_wallets(target_path: str) -> list[dict]:
    root = Path(target_path)
    if not root.exists():
        return []

    found: list[dict] = []
    for label, pattern in _WALLET_PATTERNS:
        for p in root.rglob(pattern):
            found.append({
                "type": label,
                "path": str(p.relative_to(root)),
                "size_bytes": p.stat().st_size if p.exists() else 0,
            })
    return found
