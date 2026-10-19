"""Quellen der Studio-Bibliothek: liest Medien aus Atelier, Video-Editor und Tonstudio – NUR lesend.

Je Quelle ein kleiner Leser, der Einträge (dict) liefert. Gemeinsame Regeln: keine Symlinks, nichts außerhalb des
Projekts, kaputte Begleitdateien (.json) werden ignoriert, die Datei erscheint trotzdem.
"""
from __future__ import annotations

import json
from pathlib import Path

IMAGE_EXT = {"png", "jpg", "jpeg", "webp", "gif"}
VIDEO_EXT = {"mp4", "mov", "webm", "mkv", "m4v"}
AUDIO_EXT = {"mp3", "wav", "m4a", "ogg", "flac", "aac", "opus"}


def ext(p: Path) -> str:
    return p.suffix.lower().lstrip(".")


def inside(root: Path, p: Path) -> bool:
    """Liegt `p` wirklich im Projekt (auch nach dem Auflösen) und ist es selbst kein Symlink?"""
    try:
        return not p.is_symlink() and p.resolve().is_relative_to(root.resolve())
    except OSError:
        return False


def sidecar(p: Path) -> dict:
    try:
        data = json.loads(p.with_name(p.name + ".json").read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def read_json(p: Path) -> dict:
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def files(root: Path, sub: str, exts: set[str]):
    d = root / sub
    if not d.is_dir() or not inside(root, d):
        return
    for p in sorted(d.iterdir()):
        if p.is_file() and ext(p) in exts and inside(root, p):
            yield p


def _num(v) -> float | None:
    try:
        n = float(v)
        return int(n) if n.is_integer() else n
    except (TypeError, ValueError):
        return None


def atelier(root: Path, make) -> list[dict]:
    out = []
    for sub in ("images", "output"):
        for p in files(root, f"atelier/{sub}", IMAGE_EXT):
            out.append(make(p, "image", "ai", "atelier", sidecar(p)))
    for job_file in files(root, "atelier/videos", {"json"}):
        job = read_json(job_file)
        rel = job.get("video_rel")
        if job.get("status") != "completed" or not isinstance(rel, str):
            continue
        p = root / "atelier" / rel
        if p.is_file() and inside(root, p) and ext(p) in VIDEO_EXT:
            out.append(make(p, "video", "ai", "atelier", {**job, "duration": _num(job.get("duration"))}))
    for p in files(root, "atelier/films", VIDEO_EXT):
        out.append(make(p, "video", "ai", "atelier", sidecar(p)))
    for p in files(root, "atelier/audio", AUDIO_EXT):
        out.append(make(p, "music", "ai", "atelier", sidecar(p)))
    chars = root / "atelier/characters"
    if chars.is_dir() and inside(root, chars):
        for d in sorted(chars.iterdir()):
            cfg = d / "character.json"
            if d.is_dir() and inside(root, d) and cfg.is_file() and inside(root, cfg):
                meta = read_json(cfg)
                thumb = next(files(root, f"atelier/characters/{d.name}", IMAGE_EXT), None)
                out.append(make(cfg, "element", "ai", "atelier", meta, name=meta.get("name"), thumb=thumb))
    return out


def videoeditor(root: Path, make) -> list[dict]:
    return [make(p, "video", "upload", "videoeditor", {}) for p in files(root, "videoeditor/originals", VIDEO_EXT)]


def tonstudio(root: Path, make) -> list[dict]:
    out = []
    for p in files(root, "tonstudio/clips", AUDIO_EXT):
        meta = sidecar(p)
        origin = "upload" if meta.get("origin") == "upload" else "ai"
        out.append(make(p, "music", origin, "tonstudio", meta, name=meta.get("name")))
    return out


def studio(root: Path, make) -> list[dict]:
    out = [make(p, "image", "ai", "studio", sidecar(p)) for p in files(root, "studio/media/images", IMAGE_EXT)]
    for p in files(root, "studio/media/music", AUDIO_EXT):
        meta = sidecar(p)
        out.append(make(p, "music", "ai", "studio_music", {**meta, "prompt": meta.get("description")},
                        name=(meta.get("description") or "")[:60] or None))
    for p in files(root, "studio/media/voice", AUDIO_EXT):
        meta = sidecar(p)
        out.append(make(p, "audio", "ai", "studio_voice", {**meta, "prompt": meta.get("text")}, name=(meta.get("text") or "")[:60] or None))
    out += [make(p, "image", "ai", "studio_free", sidecar(p)) for p in files(root, "studio/media/free", IMAGE_EXT)]
    out += [make(p, "image", "ai", "studio_probe", sidecar(p)) for p in files(root, "studio/media/probes", IMAGE_EXT)]   # G2
    for p in files(root, "studio/media/uploads", IMAGE_EXT | VIDEO_EXT | AUDIO_EXT):      # eigenes Material (7a)
        meta = sidecar(p)
        kind = "image" if ext(p) in IMAGE_EXT else "video" if ext(p) in VIDEO_EXT else "audio"
        name = str(meta.get("name") or "").rsplit(".", 1)[0] or None
        out.append(make(p, kind, "upload", "studio_upload", {**meta, "duration": _num(meta.get("duration"))}, name=name))
    for p in files(root, "studio/renders", VIDEO_EXT):
        meta = sidecar(p)
        out.append(make(p, "video", "ai", "studio_render", {**meta, "duration": _num(meta.get("duration"))}))
    for p in files(root, "studio/media/videos", VIDEO_EXT):
        meta = sidecar(p)
        out.append(make(p, "video", "ai", "studio", {**meta, "duration": _num(meta.get("duration"))}))
    return out


READERS = (atelier, videoeditor, tonstudio, studio)
