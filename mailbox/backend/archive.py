"""Das Mailarchiv auf der Platte (Spec §5/§5a). Es löscht **nie**: Dateien werden geschrieben oder umgezogen.

Aufbau: <archiv>/<konto-adresse>/<ordner>/<jjjj>/<jjjj-mm-tt_hhmm>_<kurzbetreff>_<hash8>.eml
Alle Pfadteile bildet nur der Server aus geprüften bzw. bereinigten Werten – nie roh aus der Mail.
"""
from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from . import paths

_SUBJ_OK = re.compile(r"[^A-Za-z0-9äöüÄÖÜß_-]+")
_SEG_OK = re.compile(r"[^A-Za-z0-9äöüÄÖÜß._-]+")
_ADDR_OK = re.compile(r"^[A-Za-z0-9._%+'-]{1,64}@[A-Za-z0-9.-]{1,253}$")
SUBJECT_MAX = 60
MANIFEST = "MANIFEST.tsv"
_HEAD = "# zeit\tpfad\tsha256\tmessage_id\tserver_ordner\tstatus\n"


class ArchiveError(ValueError):
    pass


def _account_dir(address: str) -> str:
    if not isinstance(address, str) or not _ADDR_OK.match(address) or ".." in address:
        raise ValueError("ungültige Kontoadresse für das Archiv")
    return address.lower()


def folder_dir(name: str) -> str:
    """IMAP-Ordner → sicherer relativer Pfad. Hierarchie (/ oder .) bleibt als Unterordner erhalten."""
    parts = [p for p in re.split(r"[/]", name or "")] or [""]
    out = []
    for p in parts:
        seg = _SEG_OK.sub("_", p).strip(".") or "_"
        out.append(seg[:80])
    return "/".join(out)


def _stamp(date: str) -> tuple[str, str]:
    try:
        d = datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        return d.strftime("%Y"), d.strftime("%Y-%m-%d_%H%M")
    except (TypeError, ValueError):
        return "0000", "0000-00-00_0000"


def file_name(date: str, subject: str, sha256: str) -> str:
    year, stamp = _stamp(date)
    subj = _SUBJ_OK.sub("_", subject or "").strip("_-")[:SUBJECT_MAX].strip("_-")
    return f"{stamp}_{subj}_{sha256[:8]}.eml"


def target(address: str, folder: str, name: str) -> str:
    year = name[:4] if re.match(r"^\d{4}-", name) else "0000"
    return f"{_account_dir(address)}/{folder_dir(folder)}/{year}/{name}"


def _abs(rel: str) -> Path:
    root = paths.archive_root().resolve()
    p = (root / rel).resolve()
    if not p.is_relative_to(root) or p == root:
        raise ArchiveError("Pfad außerhalb des Archivs")
    return p


def _write_new(dest: Path, raw: bytes) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(f".{dest.name}.{os.getpid()}.tmp")
    try:
        with open(tmp, "xb") as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, dest)
    finally:
        tmp.unlink(missing_ok=True)


def store(address: str, folder: str, raw: bytes, *, date: str, subject: str) -> str:
    """Rohmail ablegen. Gleiche Mail (Hash) im gleichen Ordner → dieselbe Datei, nichts Neues. Rückgabe: relativer Pfad."""
    sha = hashlib.sha256(raw).hexdigest()
    rel = target(address, folder, file_name(date, subject, sha))
    dest = _abs(rel)
    if dest.exists():
        if hashlib.sha256(dest.read_bytes()).hexdigest() != sha:
            raise ArchiveError("andere Datei mit gleichem Namen im Archiv")
        return rel
    _write_new(dest, raw)
    return rel


def move(rel: str, address: str, folder: str) -> str:
    """Ordnerwechsel auf dem Server → Datei umziehen. Überschreibt nie; Quelle bleibt bei Konflikt liegen.

    Erst neuer Name per Hardlink (schlägt fehl, wenn das Ziel existiert), dann – nur wenn beide Namen auf dieselben
    Daten zeigen – den alten Namen lösen. Es gibt keinen Moment ohne Datei, und Daten werden nie gelöscht.
    """
    src = _abs(rel)
    new = target(address, folder, src.name)
    if new == rel:
        return rel
    dest = _abs(new)
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(src, dest)
    except FileExistsError:
        if dest.read_bytes() == src.read_bytes():
            return new
        raise ArchiveError("Ziel belegt – nichts überschrieben") from None
    if os.path.samefile(src, dest):
        src.unlink()  # nur der alte Name; die Daten liegen unter dem neuen Namen (gleiche Inode)
    return new


def read(rel: str) -> bytes:
    p = _abs(rel)
    if not p.is_file():
        raise ArchiveError("nicht im Archiv")
    return p.read_bytes()


def _clean(v: str) -> str:
    return re.sub(r"[\t\r\n]+", " ", v or "")[:500]


def manifest_add(address: str, rel: str, message_id: str, server_folder: str, status: str) -> None:
    f = _abs(f"{_account_dir(address)}/{MANIFEST}")
    sha = hashlib.sha256(read(rel)).hexdigest()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    f.parent.mkdir(parents=True, exist_ok=True)
    new = not f.exists()
    with open(f, "a", encoding="utf-8") as fh:
        if new:
            fh.write(_HEAD)
        fh.write("\t".join([now, _clean(rel), sha, _clean(message_id), _clean(server_folder), _clean(status)]) + "\n")
