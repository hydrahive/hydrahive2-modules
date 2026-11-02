"""Streaming-Aufnahme unvertrauenswürdiger Artefakte ohne Ausführung."""
from __future__ import annotations

import hashlib
import os
import uuid

from . import artifacts
from .files import cases_root

MAX_FILES_PER_REQUEST = 5


def discard_upload(case_id: str, artifact: dict) -> None:
    """Aufgenommenes Artefakt samt Metadaten wieder entfernen."""
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
    """Datei aus einem Web-Upload in den Fall übernehmen.

    Der Strom landet zuerst in einer `.part`-Datei im Fallordner. Erst nach
    vollständigem Schreiben folgen Typprüfung, Hash, Grenz- und Dublettenprüfung.
    Erst dann wird die Datei atomar zum Original und danach nur noch lesbar.
    """
    original_name = artifacts.clean_name(getattr(upload, "filename", "") or "")
    artifact_id = str(uuid.uuid4())
    input_dir = cases_root(case_id) / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    temporary = input_dir / f".{artifact_id}.part"
    size = 0
    digest = hashlib.sha256()
    head = b""
    try:
        with temporary.open("xb") as destination:
            while chunk := await upload.read(artifacts.CHUNK_SIZE):
                size += len(chunk)
                if size > artifacts.MAX_ARTIFACT_BYTES:
                    return {"ok": False, "original_name": original_name,
                            "error": "reverse_artifact_too_large"}
                if len(head) < 16:
                    head += chunk[:16 - len(head)]
                digest.update(chunk)
                destination.write(chunk)
            destination.flush()
            os.fsync(destination.fileno())
        if size == 0:
            return {"ok": False, "original_name": original_name,
                    "error": "reverse_artifact_empty"}
        detected = artifacts.admitted_kind(temporary, artifacts.detect_kind(head))
        if detected == "unsafe-archive":
            return {"ok": False, "original_name": original_name,
                    "error": "reverse_artifact_archive_unsafe"}
        if detected is None or (kind is not None and kind != detected):
            return {"ok": False, "original_name": original_name,
                    "error": "reverse_artifact_type_unknown"}
        if artifacts.case_size_exceeded(input_dir, incoming=size):
            return {"ok": False, "original_name": original_name,
                    "error": "reverse_case_size_exceeded"}
        sha256 = digest.hexdigest()
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
