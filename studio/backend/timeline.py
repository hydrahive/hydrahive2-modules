"""Schnittfassung des Studios (Spec „Bauplan Etappe 4“, 4a): studio/timelines/main.json.

Eine Fassung je Projekt, Spur V1 (Video). Gespeichert wird immer die ganze Fassung mit `revision` gegen
gleichzeitige Änderungen aus einem anderen Tab. Jede Prüfregel lehnt die ganze Fassung ab (nichts wird still
verworfen außer unbekannten Feldern).
"""
from __future__ import annotations

import math
from typing import Any

from . import plan
from ._sources import IMAGE_EXT, VIDEO_EXT
from ._timeline_plan import clips_from_scenes
from ._store import is_id, new_id, read_json, root, safe_rel, write_json

MAX_CLIPS = 2000
MAX_SECONDS = 4 * 3600
FPS_ALLOWED = (24, 25, 30)
FPS_DEFAULT = 25
KINDS = ("video", "image", "placeholder")
_EXT = {"video": VIDEO_EXT, "image": IMAGE_EXT}


class Invalid(plan.PlanError):
    def __init__(self) -> None:
        super().__init__("studio_timeline_invalid")


def _path(pid: str):
    return root(pid) / "timelines" / "main.json"


def empty() -> dict:
    return {"revision": 0, "fps": FPS_DEFAULT, "tracks": [{"id": "V1", "kind": "video", "clips": []}]}


def _num(v: Any) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
        raise Invalid()
    return v


def _text(v: Any, n: int) -> str:
    return v.strip()[:n] if isinstance(v, str) else ""


def _clip(pid: str, raw: Any) -> dict:
    if not isinstance(raw, dict) or raw.get("kind") not in KINDS:
        raise Invalid()
    kind = raw["kind"]
    start, t_in, t_out = _num(raw.get("start")), _num(raw.get("in")), _num(raw.get("out"))
    if t_in >= t_out or start + (t_out - t_in) > MAX_SECONDS:
        raise Invalid()
    media = raw.get("media_rel") or ""
    if kind == "placeholder":
        if media:
            raise Invalid()
    elif safe_rel(pid, media, _EXT[kind]) is None:
        raise Invalid()
    return {
        "id": raw["id"] if is_id(raw.get("id")) else new_id(), "kind": kind, "start": start, "in": t_in, "out": t_out,
        "media_rel": media, "scene_id": raw.get("scene_id") if is_id(raw.get("scene_id")) else "",
        "shot_id": raw.get("shot_id") if is_id(raw.get("shot_id")) else "", "label": _text(raw.get("label"), 200),
    }


def clean(pid: str, data: Any) -> dict:
    """Prüft eine Fassung vollständig; wirft Invalid bei jeder Verletzung."""
    if not isinstance(data, dict):
        raise Invalid()
    tracks = data.get("tracks")
    if not isinstance(tracks, list) or len(tracks) > 1:
        raise Invalid()
    raw_clips = (tracks[0] or {}).get("clips") if tracks and isinstance(tracks[0], dict) else []
    if not isinstance(raw_clips, list) or len(raw_clips) > MAX_CLIPS:
        raise Invalid()
    fps = data.get("fps") if data.get("fps") in FPS_ALLOWED else FPS_DEFAULT
    return {"fps": fps, "tracks": [{"id": "V1", "kind": "video", "clips": [_clip(pid, c) for c in raw_clips]}]}


def load(pid: str) -> dict:
    """Gespeicherte Fassung oder leer; kaputte/unpassende Dateien lesen sich als leer (nichts wird angelegt)."""
    raw = read_json(_path(pid), None)
    if not isinstance(raw, dict):
        return empty()
    try:
        tl = clean(pid, raw)
    except plan.PlanError:
        return empty()
    rev = raw.get("revision")
    return {"revision": rev if isinstance(rev, int) and not isinstance(rev, bool) and rev >= 0 else 0, **tl}


def save(pid: str, data: Any) -> dict:
    tl = clean(pid, data)
    return _write(pid, tl, data.get("revision"))


def _write(pid: str, tl: dict, revision: Any) -> dict:
    current = load(pid)["revision"]
    if revision != current or isinstance(revision, bool):
        raise plan.PlanError("studio_timeline_conflict", 409)
    out = {"revision": current + 1, **tl}
    write_json(root(pid, create=True) / "timelines" / "main.json", out)
    return out


def from_plan(pid: str, *, replace: bool) -> dict:
    """V1 aus dem Drehbuch: Video → Videoclip, nur Bild → Standbild, sonst Platzhalter; lückenlos, in Reihenfolge."""
    current = load(pid)
    if current["tracks"][0]["clips"] and not replace:
        raise plan.PlanError("studio_timeline_not_empty", 409)
    clips = clips_from_scenes(pid, plan.list_scenes(pid))
    if not clips:
        raise plan.PlanError("studio_timeline_no_shots")
    tl = clean(pid, {"fps": current["fps"], "tracks": [{"clips": clips}]})
    return _write(pid, tl, current["revision"])
