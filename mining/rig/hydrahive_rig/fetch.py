"""Miner herunterladen, Prüfsumme kontrollieren, sicher entpacken.

Ablage: <state>/miners/<name>-<version>/ (gehört hh-rig). Vor jedem Start wird
die Prüfsumme des Archivs erneut kontrolliert (Datei liegt neben dem Entpackten).
Entpackt wird nur, was im Archiv unterhalb eines Ordners liegt — keine
absoluten Pfade, kein ``..``, keine Links nach außen.
"""
from __future__ import annotations

import hashlib
import logging
import shutil
import tarfile
import urllib.request
from pathlib import Path

from .catalog import miner

logger = logging.getLogger("hydrahive_rig")
MAX_BYTES = 200 * 1024 * 1024


class FetchError(RuntimeError):
    pass


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _download(url: str, dest: Path) -> None:
    if not url.startswith("https://github.com/"):
        raise FetchError("url_not_allowed")
    req = urllib.request.Request(url, headers={"User-Agent": "hydrahive-rig"})
    with urllib.request.urlopen(req, timeout=60) as r, dest.open("wb") as out:  # URL oben geprüft (nur github.com)
        total = 0
        while chunk := r.read(1 << 20):
            total += len(chunk)
            if total > MAX_BYTES:
                raise FetchError("download_too_large")
            out.write(chunk)


def _check_members(tf: tarfile.TarFile, target: Path) -> list[tarfile.TarInfo]:
    """Eigene Prüfung, weil Debian 12 (Python 3.11.2) den ``data``-Filter noch nicht hat.

    Erlaubt nur normale Dateien und Ordner innerhalb von ``target``; Links nur,
    wenn ihr Ziel ebenfalls innerhalb bleibt. Keine Geräte, FIFOs, setuid.
    """
    root = target.resolve()
    ok = []
    for m in tf.getmembers():
        dest = (root / m.name).resolve()
        if m.name.startswith("/") or not dest.is_relative_to(root):
            raise FetchError(f"unsafe_path:{m.name[:60]}")
        if m.issym() or m.islnk():
            link_dest = (dest.parent / m.linkname).resolve() if m.issym() else (root / m.linkname).resolve()
            if m.linkname.startswith("/") or not link_dest.is_relative_to(root):
                raise FetchError(f"unsafe_link:{m.name[:60]}")
        elif not (m.isfile() or m.isdir()):
            raise FetchError(f"unsafe_type:{m.name[:60]}")
        m.mode &= 0o755  # kein setuid/setgid, nichts für alle beschreibbar
        ok.append(m)
    return ok


def _safe_extract(archive: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:*") as tf:
        members = _check_members(tf, target)
        if hasattr(tarfile, "data_filter"):
            tf.extractall(target, members=members, filter="data")
        else:
            tf.extractall(target, members=members)  # Mitglieder oben geprüft


def ensure(name: str, state_dir: Path, *, download=_download) -> Path:
    """Pfad zur ausführbaren Datei. Lädt bei Bedarf und prüft immer die Prüfsumme."""
    m = miner(name)
    base = state_dir / "miners" / f"{name}-{m['version']}"
    archive = base / "archive.tgz"
    exe = base / "files" / m["binary"]
    if archive.exists() and sha256_of(archive) == m["sha256"] and exe.is_file():
        return exe
    shutil.rmtree(base, ignore_errors=True)
    base.mkdir(parents=True)
    logger.info("Lade %s %s …", name, m["version"])
    tmp = base / "download.part"
    download(m["url"], tmp)
    got = sha256_of(tmp)
    if got != m["sha256"]:
        shutil.rmtree(base, ignore_errors=True)
        raise FetchError(f"sha256_mismatch:{got[:12]}")
    tmp.rename(archive)
    _safe_extract(archive, base / "files")
    if not exe.is_file():
        raise FetchError("binary_missing")
    exe.chmod(0o755)
    return exe
