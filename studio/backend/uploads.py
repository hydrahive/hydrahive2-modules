"""Eigenes Material hochladen (Spec „Bauplan Etappe 7“, 7a): Bilder, Videos, Ton → studio/media/uploads/.

Der ursprüngliche Name steht nur in der Begleitdatei, nie im Pfad. Die Größe wird beim Schreiben gezählt (Abbruch bei
Überschreitung), der Inhalt geprüft: Bild an der Signatur, Video/Ton mit ffprobe. Fehler gelten je Datei – die übrigen
werden trotzdem übernommen.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath

from . import plan
from ._sources import AUDIO_EXT, IMAGE_EXT, VIDEO_EXT
from ._store import new_id, root, write_json
from .speech import probe_seconds

UPLOAD_DIR = "studio/media/uploads"
MAX_FILES = 20
LIMITS = {"image": 25 * 1024 * 1024, "audio": 200 * 1024 * 1024, "video": 2 * 1024 * 1024 * 1024}
CHUNK = 1024 * 1024
_SIGNATURES = {"png": (b"\x89PNG\r\n\x1a\n",), "jpg": (b"\xff\xd8\xff",), "jpeg": (b"\xff\xd8\xff",),
               "gif": (b"GIF87a", b"GIF89a"), "webp": (b"RIFF",)}


class Rejected(plan.PlanError):
    pass


def kind_of(ext: str) -> str | None:
    return "image" if ext in IMAGE_EXT else "video" if ext in VIDEO_EXT else "audio" if ext in AUDIO_EXT else None


def clean_name(filename: str) -> str:
    """Nur der letzte Teil, ohne Pfad (auch Windows-Pfade), höchstens 120 Zeichen."""
    name = PureWindowsPath(PurePosixPath(filename or "").name).name.strip().replace("\x00", "")
    return name[:120] or "Datei"


def _image_ok(head: bytes, ext: str) -> bool:
    sig = _SIGNATURES.get(ext, ())
    return any(head.startswith(s) for s in sig) and (ext != "webp" or head[8:12] == b"WEBP")


async def save(pid: str, upload, *, only: str | None = None) -> dict:
    """Eine Datei speichern. Gibt {ok, name, kind, rel, size, duration?} bzw. {ok: False, name, error} zurück."""
    name = clean_name(getattr(upload, "filename", "") or "")
    ext = Path(name).suffix.lower().lstrip(".")
    kind = kind_of(ext)
    try:
        if not kind or (only and kind != only):
            raise Rejected("studio_upload_invalid")
        target_dir = root(pid, create=True) / "media" / "uploads"
        target_dir.mkdir(parents=True, exist_ok=True)
        fid = new_id()
        target = target_dir / f"{fid}.{ext}"
        tmp = target_dir / f".{fid}.part"
        size, head = 0, b""
        try:
            with tmp.open("wb") as out:
                while chunk := await upload.read(CHUNK):
                    size += len(chunk)
                    if size > LIMITS[kind]:
                        raise Rejected("studio_upload_too_large", 413)
                    if len(head) < 16:
                        head += chunk[:16 - len(head)]
                    out.write(chunk)
            if size == 0:
                raise Rejected("studio_upload_empty")
            duration = None
            if kind == "image":
                if not _image_ok(head, ext):
                    raise Rejected("studio_upload_invalid")
            else:
                duration = probe_seconds(tmp)                  # Video: auch die Tonspur zählt als „lesbar“
                if duration is None:
                    raise Rejected("studio_upload_invalid")
            os.replace(tmp, target)
        finally:
            tmp.unlink(missing_ok=True)
    except plan.PlanError as e:
        return {"ok": False, "name": name, "error": e.code, "status": e.status}
    meta = {"name": name, "kind": kind, "size": size, "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            **({"duration": duration} if duration else {})}
    write_json(target.with_name(target.name + ".json"), meta)
    return {"ok": True, "name": name, "kind": kind, "rel": f"{UPLOAD_DIR}/{target.name}", "size": size,
            **({"duration": duration} if duration else {})}


async def save_many(pid: str, files: list) -> dict:
    if not files:
        raise plan.PlanError("studio_upload_empty")
    if len(files) > MAX_FILES:
        raise plan.PlanError("studio_upload_too_many")
    out = []
    for f in files:
        r = await save(pid, f)
        r.pop("status", None)
        out.append(r)
    return {"files": out}


async def add_reference(pid: str, element_id: str, upload) -> dict:
    """Bild hochladen und als Referenz an den Baustein hängen (höchstens 8)."""
    el = next((e for e in plan.list_elements(pid) if e["id"] == element_id), None)
    if el is None:
        raise plan.PlanError("studio_not_found", 404)
    if len(el.get("references") or []) >= 8:
        raise plan.PlanError("studio_references_full")
    r = await save(pid, upload, only="image")
    if not r["ok"]:
        raise plan.PlanError(r["error"], r["status"])
    return plan.save_element(pid, {**el, "references": [*el["references"], r["rel"]]}, element_id)
