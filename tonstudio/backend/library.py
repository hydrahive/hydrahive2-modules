"""Bibliothek: Quellen eines Projekts (SPEC.md §4).

- Eigene Clips unter ``tonstudio/clips/`` (erzeugt oder hochgeladen), mit Sidecar.
- Projekt-Audio überall sonst im Workspace (z. B. ``generated/``, ``atelier/audio/``). Es wird nur referenziert,
  nie kopiert oder verändert (kein Silo, wie im Video-Editor).
- Hochladen: Endung, Größe UND Inhalt (ffprobe) prüfen. Gespeichert unter einer neuen ID, Originalname im Sidecar.
- Löschen: nur eigene Clips, nie Projektdateien.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from . import storage
from ._ffprobe import probe_audio

_SKIP_DIRS = {"tonstudio", ".git", "node_modules", "__pycache__", ".venv", "videoeditor"}


class UploadError(ValueError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_sidecar(clip: Path, meta: dict) -> None:
    tmp = clip.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(meta, ensure_ascii=False, indent=2), "utf-8")
    tmp.replace(clip.with_suffix(".json"))


def _read_sidecar(clip: Path) -> dict:
    try:
        return json.loads(clip.with_suffix(".json").read_text("utf-8"))
    except (OSError, ValueError):
        return {}


def _own_clips(project_id: str) -> list[dict]:
    out = []
    for p in storage.clips_dir(project_id).iterdir():
        if p.is_file() and storage.audio_ext(p.name) and storage.is_valid_id(p.stem):
            meta = _read_sidecar(p)
            out.append({
                "source_rel": storage.rel_to_workspace(project_id, p), "origin": meta.get("origin", "upload"),
                "name": meta.get("name") or p.name, "duration": meta.get("duration"),
                "model": meta.get("model"), "backend": meta.get("backend"), "prompt": meta.get("prompt"),
                "created_at": meta.get("created_at"), "size_bytes": p.stat().st_size,
            })
    return out


def _project_audio(project_id: str) -> list[dict]:
    root = storage.workspace_root(project_id)
    out = []
    for p in root.rglob("*"):
        rel = p.relative_to(root)
        if not p.is_file() or rel.parts[0] in _SKIP_DIRS or any(x.startswith(".") for x in rel.parts):
            continue
        if storage.audio_ext(p.name):
            out.append({"source_rel": str(rel), "origin": "project", "name": p.name, "duration": None,
                        "model": None, "backend": None, "prompt": None,
                        "created_at": datetime.fromtimestamp(p.stat().st_mtime, timezone.utc)
                        .strftime("%Y-%m-%dT%H:%M:%SZ"), "size_bytes": p.stat().st_size})
    return out


def list_sources(project_id: str) -> list[dict]:
    items = _own_clips(project_id) + _project_audio(project_id)
    items.sort(key=lambda i: i.get("created_at") or "", reverse=True)
    return items


async def add_upload(project_id: str, filename: str, data: bytes, *, user: str) -> dict:
    if len(data) > storage.MAX_UPLOAD_BYTES:
        raise UploadError(f"Datei zu groß (höchstens {storage.MAX_UPLOAD_BYTES // (1024 * 1024)} MB)")
    ext = storage.audio_ext(filename or "")
    if not ext:
        raise UploadError(f"Format nicht unterstützt (erlaubt: {', '.join(storage.AUDIO_EXT)})")
    clip_id = storage.new_id()
    clip = storage.clips_dir(project_id) / f"{clip_id}.{ext}"
    clip.write_bytes(data)
    info = await probe_audio(clip)
    if info is None:
        clip.unlink(missing_ok=True)
        raise UploadError("Die Datei enthält kein lesbares Audio")
    name = Path(filename).name[:200]
    meta = {"origin": "upload", "name": name, "created_at": _now(), "created_by": user, **info}
    write_sidecar(clip, meta)
    return {"source_rel": storage.rel_to_workspace(project_id, clip), "origin": "upload", "name": name,
            "duration": info["duration"], "created_at": meta["created_at"]}


def delete_clip(project_id: str, source_rel: str) -> bool:
    """Nur eigene Clips (``tonstudio/clips/<id>.<ext>``) löschen. Projektdateien bleiben immer unberührt."""
    path = storage.safe_under(storage.workspace_root(project_id), source_rel)
    clips = storage.clips_dir(project_id).resolve()
    if path is None or path.parent != clips or not path.is_file() or not storage.is_valid_id(path.stem):
        return False
    path.unlink()
    path.with_suffix(".json").unlink(missing_ok=True)
    return True
