"""Schnittfassung des Studios (Spec „Bauplan Etappe 4“, 4a): studio/timelines/main.json.

Eine Fassung je Projekt, Spur V1 (Video). Gespeichert wird immer die ganze Fassung mit `revision` gegen
gleichzeitige Änderungen aus einem anderen Tab. Jede Prüfregel lehnt die ganze Fassung ab (nichts wird still
verworfen außer unbekannten Feldern).
"""
from __future__ import annotations

import math
from itertools import pairwise
from typing import Any

from . import plan
from ._sources import IMAGE_EXT, VIDEO_EXT
from ._store import is_id, new_id, read_json, root, safe_rel, write_json
from ._timeline_plan import _video_length, clips_from_scenes

MAX_CLIPS = 2000
MAX_SECONDS = 4 * 3600
FPS_ALLOWED = (24, 25, 30)
FPS_DEFAULT = 25
KINDS = ("video", "image", "placeholder")
IMAGE_SECONDS = 5                          # Standbild wie im Browser (frontend/cutEdit.ts IMAGE_SECONDS)
EPS = 1e-6                                 # Gleitkomma-Reste beim Aneinanderstoßen zählen nicht als Überlappung
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


def _clip(pid: str, raw: Any, *, on_load: bool = False) -> dict:
    """Ein Clip. Beim Laden (`on_load`) wird ein Clip, dessen Medium inzwischen fehlt, zum Platzhalter (`missing`)."""
    if not isinstance(raw, dict) or raw.get("kind") not in KINDS:
        raise Invalid()
    kind = raw["kind"]
    start, t_in, t_out = _num(raw.get("start")), _num(raw.get("in")), _num(raw.get("out"))
    if t_in >= t_out or start + (t_out - t_in) > MAX_SECONDS:
        raise Invalid()
    media = raw.get("media_rel") or ""
    missing = False
    if kind == "placeholder":
        if media:
            raise Invalid()
        missing = raw.get("missing") is True
    elif safe_rel(pid, media, _EXT[kind]) is None:
        if not on_load:
            raise Invalid()
        kind, media, missing = "placeholder", "", True
    out = {
        "id": raw["id"] if is_id(raw.get("id")) else new_id(), "kind": kind, "start": start, "in": t_in, "out": t_out,
        "media_rel": media, "scene_id": raw.get("scene_id") if is_id(raw.get("scene_id")) else "",
        "shot_id": raw.get("shot_id") if is_id(raw.get("shot_id")) else "", "label": _text(raw.get("label"), 200),
    }
    if missing:
        out["missing"] = True
    return out


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
    clips = sorted((_clip(pid, c) for c in raw_clips), key=lambda c: c["start"])
    for a, b in pairwise(clips):                # magnetische Hauptspur: Clips dürfen sich nicht überlappen
        if b["start"] < _end(a) - EPS:
            raise Invalid()
    return {"fps": fps, "tracks": [{"id": "V1", "kind": "video", "clips": clips}]}


def _end(c: dict) -> float:
    return c["start"] + c["out"] - c["in"]


def _loaded_clips(pid: str, raw: dict) -> list[dict]:
    tracks = raw.get("tracks")
    first = tracks[0] if isinstance(tracks, list) and tracks and isinstance(tracks[0], dict) else {}
    ok = []
    for c in (first.get("clips") if isinstance(first.get("clips"), list) else [])[:MAX_CLIPS]:
        try:
            ok.append(_clip(pid, c, on_load=True))
        except plan.PlanError:
            continue                                     # einzelner kaputter Clip: überspringen, Rest bleibt
    out: list[dict] = []
    for c in sorted(ok, key=lambda c: c["start"]):
        if not out or c["start"] >= _end(out[-1]) - EPS:  # überlappender Clip (alte/kaputte Datei) wird übersprungen
            out.append(c)
    return out


def load(pid: str) -> dict:
    """Gespeicherte Fassung oder leer (nichts wird angelegt). Kaputte Clips werden übersprungen, Clips mit
    gelöschtem Medium werden Platzhalter – die übrige Arbeit geht nie verloren."""
    raw = read_json(_path(pid), None)
    if not isinstance(raw, dict):
        return empty()
    rev = raw.get("revision")
    fps = raw.get("fps") if raw.get("fps") in FPS_ALLOWED else FPS_DEFAULT
    return {"revision": rev if isinstance(rev, int) and not isinstance(rev, bool) and rev >= 0 else 0, "fps": fps,
            "tracks": [{"id": "V1", "kind": "video", "clips": _loaded_clips(pid, raw)}]}


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


def append(pid: str, media_rel) -> dict:
    """Ein Bild (Standbild, IMAGE_SECONDS) oder Video des Studios hinten an V1 hängen (B3 „Auf die Zeitleiste“)."""
    rel = media_rel if isinstance(media_rel, str) and media_rel.startswith("studio/media/") and ".." not in media_rel else ""
    kind = "image" if rel and safe_rel(pid, rel, IMAGE_EXT) else "video" if rel and safe_rel(pid, rel, VIDEO_EXT) else ""
    if not kind:
        raise Invalid()
    current = load(pid)
    clips = current["tracks"][0]["clips"]
    start = max((_end(c) for c in clips), default=0.0)
    length = IMAGE_SECONDS if kind == "image" else _video_length(pid, rel, IMAGE_SECONDS)
    clip = {"id": new_id(), "kind": kind, "start": start, "in": 0, "out": length, "media_rel": rel, "label": rel.rsplit("/", 1)[-1]}
    tl = clean(pid, {"fps": current["fps"], "tracks": [{"clips": [*clips, clip]}]})
    return _write(pid, tl, current["revision"])


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
