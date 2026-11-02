"""Gemeinsame Artefaktprüfung: Typ, Hash, Grenzen, atomare Veröffentlichung.

Web-Upload und Samba-Eingang benutzen dieselben Regeln. Deshalb liegen sie
hier, nicht in einem der beiden Wege: so kann kein Pfad die Prüfung umgehen.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import struct
import zipfile
from pathlib import Path, PurePosixPath, PureWindowsPath

MAX_ARTIFACT_BYTES = 512 * 1024 * 1024
MAX_CASE_BYTES = 2 * 1024 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 100_000
MAX_ARCHIVE_UNCOMPRESSED = 4 * 1024 * 1024 * 1024
MAX_ARCHIVE_RATIO = 200
CHUNK_SIZE = 1024 * 1024
EXTENSIONS = {"pe": "pe", "apk": "apk", "elf": "elf", "pcap": "pcap",
              "pcapng": "pcapng", "firmware": "bin"}


def clean_name(filename: str) -> str:
    """Nur der Basisname, ohne Nulll Bytes, Traversal oder führende Punkte."""
    value = PureWindowsPath(PurePosixPath(filename or "").name).name
    value = value.replace("\x00", "").strip()[:160]
    value = re.sub(r"\.{2,}", ".", value)
    return value.strip(". ") or "Datei"


def detect_kind(head: bytes) -> str | None:
    """Grobe Magic-Erkennung. Feinschliff folgt in admitted_kind()."""
    if head.startswith(b"MZ"):
        return "pe"
    if head.startswith(b"PK\x03\x04"):
        return "zip"
    if head.startswith(b"\x7fELF"):
        return "elf"
    if head.startswith((b"\xd4\xc3\xb2\xa1", b"\xa1\xb2\xc3\xd4",
                        b"\x4d\x3c\xb2\xa1", b"\xa1\xb2\x3c\x4d")):
        return "pcap"
    if head.startswith(b"\x0a\x0d\x0d\x0a"):
        return "pcapng"
    if head.startswith(b"\xe9"):
        return "firmware"
    return None


def admitted_kind(path: Path, detected: str | None) -> str | None:
    """Strukturprüfung einer Datei auf Platte. `unsafe-archive` heißt abgelehnt."""
    if detected == "pe":
        try:
            with path.open("rb") as source:
                source.seek(0x3C)
                offset_raw = source.read(4)
                if len(offset_raw) != 4:
                    return None
                offset = struct.unpack("<I", offset_raw)[0]
                if offset > path.stat().st_size - 4:
                    return None
                source.seek(offset)
                return "pe" if source.read(4) == b"PE\x00\x00" else None
        except OSError:
            return None
    if detected != "zip":
        return detected
    try:
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            unpacked = sum(item.file_size for item in entries)
            packed = sum(item.compress_size for item in entries)
            if (len(entries) > MAX_ARCHIVE_ENTRIES
                    or unpacked > MAX_ARCHIVE_UNCOMPRESSED
                    or (unpacked > 0 and unpacked > max(packed, 1) * MAX_ARCHIVE_RATIO)):
                return "unsafe-archive"
            names = {item.filename for item in entries}
            has_manifest = "AndroidManifest.xml" in names
            has_dex = any(name.endswith(".dex") for name in names)
            return "apk" if has_manifest and has_dex else None
    except (OSError, zipfile.BadZipFile):
        return None


def case_size_exceeded(input_dir: Path, *, incoming: int) -> bool:
    """Summe der aufgenommenen Originale plus der neuen Datei gegen die Fallgrenze."""
    used = sum(
        path.stat().st_size
        for path in input_dir.glob("*")
        if path.is_file() and not path.name.endswith((".json", ".part"))
    )
    return used + incoming > MAX_CASE_BYTES


def has_hash(input_dir: Path, digest: str) -> bool:
    """True, wenn der Fall bereits ein Artefakt mit diesem SHA-256 enthält."""
    for metadata in input_dir.glob("*.json"):
        try:
            if json.loads(metadata.read_text()).get("sha256") == digest:
                return True
        except (OSError, json.JSONDecodeError):
            continue
    return False


def write_metadata(path: Path, value: dict) -> None:
    """Metadaten atomar schreiben; die Originaldatei bleibt unberührt."""
    temporary = path.with_name(f".{path.name}.part")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    os.replace(temporary, path)


def publish_artifact(*, source: Path, input_dir: Path, artifact_id: str, kind: str,
                     original_name: str, size: int, sha256: str) -> dict:
    """`.part` atomar zum Original im Fall machen und Metadaten danebenlegen."""
    target = input_dir / f"{artifact_id}.{EXTENSIONS[kind]}"
    os.replace(source, target)
    target.chmod(0o440)
    metadata = {
        "artifact_id": artifact_id,
        "original_name": original_name,
        "kind": kind,
        "size": size,
        "sha256": sha256,
        "relative_path": f"input/{target.name}",
    }
    write_metadata(target.with_suffix(target.suffix + ".json"), metadata)
    return metadata


def hash_file(path: Path) -> tuple[int, str]:
    """Größe und SHA-256 einer Datei, ohne sie vollständig zu laden."""
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as source:
        while chunk := source.read(CHUNK_SIZE):
            size += len(chunk)
            digest.update(chunk)
    return size, digest.hexdigest()


def read_head(path: Path, length: int = 16) -> bytes:
    """Erste Bytes einer Datei lesen."""
    with path.open("rb") as source:
        return source.read(length)


def iter_chunks(stream, *, size: int = CHUNK_SIZE):
    """Quelle in Stücken lesen, damit nichts vollständig im Speicher landet."""
    while chunk := stream.read(size):
        yield chunk
