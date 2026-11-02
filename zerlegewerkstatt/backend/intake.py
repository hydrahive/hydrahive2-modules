"""Projekt-Samba-Eingang: Dateien aus der Projektfreigabe sicher übernehmen.

Der Nutzer legt Dateien in `<Projekt-Workspace>/zerlegewerkstatt/eingang/<case-id>/`
ab. Dieser Scanner nimmt nur stabile reguläre Dateien auf und lässt die
Originale unverändert.

Sicherheitsregeln:
- Symlinks werden nicht geöffnet und nicht aufgenommen.
- Nur Dateien unmittelbar im Eingangsordner, keine Unterordner.
- Größe, Gerät/Inode und Änderungszeit werden vor und nach dem Kopieren
  verglichen. Ändert sich die Datei währenddessen, wird verworfen.
- Der Inhalt wird in eine private `.part`-Datei im Modul-Datenordner kopiert
  und dort geprüft. Erst danach wird er atomar zum Original im Fall.
"""
from __future__ import annotations

import hashlib
import os
import uuid
from pathlib import Path

from . import artifacts
from .files import cases_root, check_case_id, check_project_id

MAX_INTAKE_FILES = 50


def intake_root(project_id: str, case_id: str) -> Path:
    """Eingangsordner eines Falls im Projekt-Workspace (Samba-Freigabe)."""
    from hydrahive.projects._paths import workspace_path

    check_project_id(project_id)
    check_case_id(case_id)
    return workspace_path(project_id) / "zerlegewerkstatt" / "eingang" / case_id


def _stable_stat(path: Path) -> os.stat_result | None:
    """Stat ohne Symlink zu folgen; `None`, wenn kein reguläres File."""
    try:
        info = path.lstat()
    except OSError:
        return None
    if not os.path.stat.S_ISREG(info.st_mode):
        return None
    return info


def _same_file(before: os.stat_result, after: os.stat_result) -> bool:
    """Unverändert zwischen Vor- und Nachprüfung?"""
    return (
        before.st_dev == after.st_dev
        and before.st_ino == after.st_ino
        and before.st_size == after.st_size
        and before.st_mtime_ns == after.st_mtime_ns
    )


def _open_regular(path: Path):
    """Datei ohne Symlink-Folge öffnen.

    `O_NOFOLLOW` schließt das Fenster zwischen der Vorprüfung und dem Öffnen:
    Wurde die Datei inzwischen durch einen Symlink ersetzt, schlägt das Öffnen
    fehl, statt dass ein fremdes Ziel gelesen wird.
    """
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    handle = os.open(path, flags)
    try:
        info = os.fstat(handle)
        if not os.path.stat.S_ISREG(info.st_mode):
            raise OSError("kein regulaeres File")
    except OSError:
        os.close(handle)
        raise
    return handle


def _copy_out(source: Path, target: Path) -> tuple[int, str]:
    """Datei in die private `.part`-Datei kopieren und dabei hashen."""
    digest = hashlib.sha256()
    size = 0
    handle = _open_regular(source)
    with os.fdopen(handle, "rb") as reader, target.open("xb") as writer:
        while chunk := reader.read(artifacts.CHUNK_SIZE):
            size += len(chunk)
            digest.update(chunk)
            writer.write(chunk)
        writer.flush()
        os.fsync(writer.fileno())
    return size, digest.hexdigest()


def scan_intake(project_id: str, case_id: str) -> dict:
    """Eingangsordner prüfen und neue Dateien in den Fall übernehmen.

    Liefert je Datei ein Ergebnis mit stabilem Fehlercode. Fehler in einer
    Datei beenden den Lauf nicht.
    """
    check_case_id(case_id)
    check_project_id(project_id)
    source_dir = intake_root(project_id, case_id)
    input_dir = cases_root(case_id) / "input"
    input_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []
    if not source_dir.is_dir():
        return {"scanned": 0, "taken": 0, "files": results}

    candidates = sorted(
        entry for entry in source_dir.iterdir()
        if not entry.name.startswith(".") and not entry.is_dir()
    )
    if len(candidates) > MAX_INTAKE_FILES:
        return {"scanned": len(candidates), "taken": 0,
                "files": [{"ok": False, "original_name": "",
                           "error": "reverse_intake_too_many"}]}

    for entry in candidates:
        results.append(_take_one(entry, input_dir))

    taken = sum(1 for item in results if item["ok"])
    return {"scanned": len(results), "taken": taken, "files": results}


def _take_one(entry: Path, input_dir: Path) -> dict:
    """Eine Eingangsdatei prüfen und gegebenenfalls übernehmen."""
    original_name = artifacts.clean_name(entry.name)
    before = _stable_stat(entry)
    if before is None:
        return {"ok": False, "original_name": original_name,
                "error": "reverse_intake_not_regular"}
    if before.st_size == 0:
        return {"ok": False, "original_name": original_name,
                "error": "reverse_artifact_empty"}
    if before.st_size > artifacts.MAX_ARTIFACT_BYTES:
        return {"ok": False, "original_name": original_name,
                "error": "reverse_artifact_too_large"}

    artifact_id = str(uuid.uuid4())
    temporary = input_dir / f".{artifact_id}.part"
    try:
        try:
            size, sha256 = _copy_out(entry, temporary)
        except OSError:
            # Untergangen zwischen Vorprüfung und Öffnen: Datei wurde entfernt
            # oder zum Symlink. In beiden Fällen wird nichts übernommen.
            return {"ok": False, "original_name": original_name,
                    "error": "reverse_intake_changed"}
        after = _stable_stat(entry)
        if after is None or not _same_file(before, after):
            return {"ok": False, "original_name": original_name,
                    "error": "reverse_intake_changed"}
        if size != before.st_size:
            return {"ok": False, "original_name": original_name,
                    "error": "reverse_intake_changed"}

        with temporary.open("rb") as reader:
            head = reader.read(16)
        detected = artifacts.admitted_kind(temporary, artifacts.detect_kind(head))
        if detected == "unsafe-archive":
            return {"ok": False, "original_name": original_name,
                    "error": "reverse_artifact_archive_unsafe"}
        if detected is None:
            return {"ok": False, "original_name": original_name,
                    "error": "reverse_artifact_type_unknown"}
        if artifacts.case_size_exceeded(input_dir, incoming=size):
            return {"ok": False, "original_name": original_name,
                    "error": "reverse_case_size_exceeded"}
        if artifacts.has_hash(input_dir, sha256):
            return {"ok": False, "original_name": original_name,
                    "error": "reverse_artifact_duplicate"}

        metadata = artifacts.publish_artifact(
            source=temporary, input_dir=input_dir, artifact_id=artifact_id,
            kind=detected, original_name=original_name, size=size, sha256=sha256,
        )
        return {"ok": True, **metadata}
    finally:
        temporary.unlink(missing_ok=True)
