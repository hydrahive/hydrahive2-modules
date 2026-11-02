"""Streaming-Aufnahme unvertrauenswürdiger Artefakte ohne Ausführung."""
from __future__ import annotations

import hashlib
import json
import os
import re
import struct
import uuid
import zipfile
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import BinaryIO, Iterator

from .files import cases_root

MAX_FILES_PER_REQUEST = 5
MAX_ARTIFACT_BYTES = 512 * 1024 * 1024
MAX_CASE_BYTES = 2 * 1024 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 100_000
MAX_ARCHIVE_UNCOMPRESSED = 4 * 1024 * 1024 * 1024
MAX_ARCHIVE_RATIO = 200
CHUNK_SIZE = 1024 * 1024
_EXTENSIONS = {"pe": "pe", "apk": "apk", "elf": "elf", "pcap": "pcap", "pcapng": "pcapng", "firmware": "bin"}


def clean_name(filename: str) -> str:
    value = PureWindowsPath(PurePosixPath(filename or "").name).name
    value = value.replace("\x00", "").strip()[:160]
    value = re.sub(r"\.{2,}", ".", value)
    return value.strip(". ") or "Datei"


def detect_kind(head: bytes) -> str | None:
    if head.startswith(b"MZ"):
        return "pe"
    if head.startswith(b"PK\x03\x04"):
        return "zip"
    if head.startswith(b"\x7fELF"):
        return "elf"
    if head.startswith((b"\xd4\xc3\xb2\xa1", b"\xa1\xb2\xc3\xd4", b"\x4d\x3c\xb2\xa1", b"\xa1\xb2\x3c\x4d")):
        return "pcap"
    if head.startswith(b"\x0a\x0d\x0d\x0a"):
        return "pcapng"
    if head.startswith(b"\xe9"):
        return "firmware"
    return None


def iter_chunks(stream: BinaryIO, *, size: int = CHUNK_SIZE) -> Iterator[bytes]:
    while chunk := stream.read(size):
        yield chunk


def case_size_exceeded(input_dir: Path, *, incoming: int) -> bool:
    used = sum(
        p.stat().st_size for p in input_dir.glob("*")
        if p.is_file() and not p.name.endswith((".json", ".part"))
    )
    return used + incoming > MAX_CASE_BYTES


def _admitted_kind(path: Path, detected: str | None) -> str | None:
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
            if (len(entries) > MAX_ARCHIVE_ENTRIES or unpacked > MAX_ARCHIVE_UNCOMPRESSED
                    or (unpacked > 0 and unpacked > max(packed, 1) * MAX_ARCHIVE_RATIO)):
                return "unsafe-archive"
            names = {item.filename for item in entries}
            return "apk" if "AndroidManifest.xml" in names and any(name.endswith(".dex") for name in names) else None
    except (OSError, zipfile.BadZipFile):
        return None


def _has_hash(input_dir: Path, digest: str) -> bool:
    for metadata in input_dir.glob("*.json"):
        try:
            if json.loads(metadata.read_text()).get("sha256") == digest:
                return True
        except (OSError, json.JSONDecodeError):
            continue
    return False


def _publish_metadata(path: Path, value: dict) -> None:
    temporary = path.with_name(f".{path.name}.part")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    os.replace(temporary, path)


def discard_upload(case_id: str, artifact: dict) -> None:
    relative = str(artifact.get("relative_path") or "")
    target = cases_root(case_id) / relative
    input_dir = cases_root(case_id) / "input"
    try:
        target.resolve().relative_to(input_dir.resolve())
    except (OSError, ValueError):
        return
    target.unlink(missing_ok=True)
    target.with_suffix(target.suffix + ".json").unlink(missing_ok=True)


async def store_upload(case_id: str, upload, *, kind: str | None = None) -> dict:
    original_name = clean_name(getattr(upload, "filename", "") or "")
    artifact_id = str(uuid.uuid4())
    input_dir = cases_root(case_id) / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    temporary = input_dir / f".{artifact_id}.part"
    size = 0
    digest = hashlib.sha256()
    head = b""
    try:
        with temporary.open("xb") as destination:
            while chunk := await upload.read(CHUNK_SIZE):
                size += len(chunk)
                if size > MAX_ARTIFACT_BYTES:
                    return {"ok": False, "original_name": original_name, "error": "reverse_artifact_too_large"}
                if len(head) < 16:
                    head += chunk[:16 - len(head)]
                digest.update(chunk)
                destination.write(chunk)
            destination.flush()
            os.fsync(destination.fileno())
        if size == 0:
            return {"ok": False, "original_name": original_name, "error": "reverse_artifact_empty"}
        detected = _admitted_kind(temporary, detect_kind(head))
        if detected == "unsafe-archive":
            return {"ok": False, "original_name": original_name, "error": "reverse_artifact_archive_unsafe"}
        if detected is None or (kind is not None and kind != detected):
            return {"ok": False, "original_name": original_name, "error": "reverse_artifact_type_unknown"}
        kind = detected
        if case_size_exceeded(input_dir, incoming=size):
            return {"ok": False, "original_name": original_name, "error": "reverse_case_size_exceeded"}
        sha256 = digest.hexdigest()
        if _has_hash(input_dir, sha256):
            return {"ok": False, "original_name": original_name, "error": "reverse_artifact_duplicate"}
        target = input_dir / f"{artifact_id}.{_EXTENSIONS[kind]}"
        os.replace(temporary, target)
        target.chmod(0o440)
        metadata = {"artifact_id": artifact_id, "original_name": original_name, "kind": kind,
                    "size": size, "sha256": sha256, "relative_path": f"input/{target.name}"}
        _publish_metadata(target.with_suffix(target.suffix + ".json"), metadata)
        return {"ok": True, **metadata}
    finally:
        temporary.unlink(missing_ok=True)
