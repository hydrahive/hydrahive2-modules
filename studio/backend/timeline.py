"""Schnittfassung des Studios (Spec „Bauplan Etappe 4“ und „Etappe 5“): studio/timelines/main.json.

Eine Fassung je Projekt mit festen Spuren: V1 (Bild, magnetisch), A1 „Sprache“ und A2 „Musik“ (frei, Lücken = Stille).
Gespeichert wird immer die ganze Fassung mit `revision` gegen gleichzeitige Änderungen aus einem anderen Tab. Jede
Prüfregel lehnt die ganze Fassung ab (nichts wird still verworfen außer unbekannten Feldern). Fehlt beim Speichern eine
Spur (älterer Browser-Stand nur mit V1), bleibt deren gespeicherter Inhalt erhalten.
"""
from __future__ import annotations

import math
from itertools import pairwise
from typing import Any

from . import plan
from ._sources import AUDIO_EXT, IMAGE_EXT, VIDEO_EXT
from ._store import is_id, new_id, read_json, root, safe_rel, write_json
from ._timeline_plan import _video_length, clips_from_scenes

MAX_CLIPS = 2000
MAX_SECONDS = 4 * 3600
FPS_ALLOWED = (24, 25, 30)
FPS_DEFAULT = 25
KINDS = ("video", "image", "placeholder")                 # auf V1
TRACKS = (("V1", "video"), ("A1", "audio"), ("A2", "audio"))   # feste Spuren (Till, 18.10.)
IMAGE_SECONDS = 5                          # Standbild wie im Browser (frontend/cutEdit.ts IMAGE_SECONDS)
EPS = 1e-6                                 # Gleitkomma-Reste beim Aneinanderstoßen zählen nicht als Überlappung
_EXT = {"video": VIDEO_EXT, "image": IMAGE_EXT, "audio": AUDIO_EXT}


class Invalid(plan.PlanError):
    def __init__(self) -> None:
        super().__init__("studio_timeline_invalid")


def _path(pid: str):
    return root(pid) / "timelines" / "main.json"


def _tracks(clips: dict[str, list[dict]]) -> list[dict]:
    return [{"id": tid, "kind": kind, "clips": clips.get(tid, [])} for tid, kind in TRACKS]


def empty() -> dict:
    return {"revision": 0, "fps": FPS_DEFAULT, "tracks": _tracks({})}


def _num(v: Any) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
        raise Invalid()
    return v


def _text(v: Any, n: int) -> str:
    return v.strip()[:n] if isinstance(v, str) else ""


def _clip(pid: str, raw: Any, *, on_load: bool = False, audio: bool = False) -> dict:
    """Ein Clip. Beim Laden (`on_load`) wird ein Clip, dessen Medium inzwischen fehlt, zum Platzhalter (`missing`);
    auf den Tonspuren (`audio`) bleibt er ein Tonclip ohne Datei (`missing`) und wird als Stille gerendert."""
    if not isinstance(raw, dict) or raw.get("kind") not in (("audio",) if audio else KINDS):
        raise Invalid()
    kind = raw["kind"]
    start, t_in, t_out = _num(raw.get("start")), _num(raw.get("in")), _num(raw.get("out"))
    if t_in >= t_out or start + (t_out - t_in) > MAX_SECONDS:
        raise Invalid()
    media = raw.get("media_rel") or ""
    missing = False
    if kind == "placeholder" or (kind == "audio" and not media and raw.get("missing") is True):
        if media:
            raise Invalid()
        missing = raw.get("missing") is True
    elif safe_rel(pid, media, _EXT[kind]) is None:
        if not on_load:
            raise Invalid()
        kind, media, missing = ("audio" if audio else "placeholder"), "", True
    out = {
        "id": raw["id"] if is_id(raw.get("id")) else new_id(), "kind": kind, "start": start, "in": t_in, "out": t_out,
        "media_rel": media, "scene_id": raw.get("scene_id") if is_id(raw.get("scene_id")) else "",
        "shot_id": raw.get("shot_id") if is_id(raw.get("shot_id")) else "", "label": _text(raw.get("label"), 200),
    }
    if missing:
        out["missing"] = True
    return out


def clean(pid: str, data: Any, keep: dict[str, list[dict]] | None = None) -> dict:
    """Prüft eine Fassung vollständig; wirft Invalid bei jeder Verletzung. `keep`: Clips je Spur für Spuren, die in
    `data` fehlen (gespeicherter Stand) – sie werden wie neue geprüft."""
    if not isinstance(data, dict):
        raise Invalid()
    tracks = data.get("tracks")
    if not isinstance(tracks, list) or not 1 <= len(tracks) <= len(TRACKS) or not all(isinstance(t, dict) for t in tracks):
        raise Invalid()
    ids = [t.get("id", "V1") for t in tracks]                         # ohne id: V1 (Fassungen aus 4a/4b)
    if len(set(ids)) != len(ids) or "V1" not in ids or any(i not in dict(TRACKS) for i in ids):
        raise Invalid()
    given = {i: t.get("clips") for i, t in zip(ids, tracks)}
    out: dict[str, list[dict]] = {}
    for tid, kind in TRACKS:
        raw = given[tid] if tid in given else (keep or {}).get(tid, [])
        if not isinstance(raw, list) or len(raw) > MAX_CLIPS:
            raise Invalid()
        clips = sorted((_clip(pid, c, audio=kind == "audio") for c in raw), key=lambda c: c["start"])
        for a, b in pairwise(clips):            # weder auf V1 (magnetisch) noch innerhalb einer Tonspur überlappen
            if b["start"] < _end(a) - EPS:
                raise Invalid()
        out[tid] = clips
    if sum(len(c) for c in out.values()) > MAX_CLIPS:
        raise Invalid()
    fps = data.get("fps") if data.get("fps") in FPS_ALLOWED else FPS_DEFAULT
    return {"fps": fps, "tracks": _tracks(out)}


def _end(c: dict) -> float:
    return c["start"] + c["out"] - c["in"]


def _loaded_clips(pid: str, raw: Any, audio: bool) -> list[dict]:
    ok = []
    for c in (raw.get("clips") if isinstance(raw, dict) and isinstance(raw.get("clips"), list) else [])[:MAX_CLIPS]:
        try:
            ok.append(_clip(pid, c, on_load=True, audio=audio))
        except plan.PlanError:
            continue                                     # einzelner kaputter Clip: überspringen, Rest bleibt
    out: list[dict] = []
    for c in sorted(ok, key=lambda c: c["start"]):
        if not out or c["start"] >= _end(out[-1]) - EPS:  # überlappender Clip (alte/kaputte Datei) wird übersprungen
            out.append(c)
    return out


def load(pid: str) -> dict:
    """Gespeicherte Fassung oder leer (nichts wird angelegt). Kaputte Clips werden übersprungen, Clips mit
    gelöschtem Medium werden Platzhalter bzw. stumme Tonclips – die übrige Arbeit geht nie verloren. Fehlende
    Tonspuren (Fassungen vor Etappe 5) kommen leer dazu; die Datei bleibt dabei unverändert."""
    raw = read_json(_path(pid), None)
    if not isinstance(raw, dict):
        return empty()
    rev = raw.get("revision")
    fps = raw.get("fps") if raw.get("fps") in FPS_ALLOWED else FPS_DEFAULT
    stored = raw.get("tracks") if isinstance(raw.get("tracks"), list) else []
    by_id: dict[str, Any] = {}
    for i, t in enumerate(stored):
        if isinstance(t, dict):
            by_id.setdefault(t.get("id") or ("V1" if i == 0 else ""), t)
    clips = {tid: _loaded_clips(pid, by_id.get(tid), kind == "audio") for tid, kind in TRACKS}
    return {"revision": rev if isinstance(rev, int) and not isinstance(rev, bool) and rev >= 0 else 0, "fps": fps,
            "tracks": _tracks(clips)}


def clips_of(tl: dict, track: str = "V1") -> list[dict]:
    return next((t["clips"] for t in tl["tracks"] if t["id"] == track), [])


def all_clips(tl: dict) -> list[dict]:
    return [c for t in tl["tracks"] for c in t["clips"]]


def _keep(tl: dict) -> dict[str, list[dict]]:
    return {t["id"]: t["clips"] for t in tl["tracks"]}


def save(pid: str, data: Any) -> dict:
    tl = clean(pid, data, _keep(load(pid)))
    return _write(pid, tl, data.get("revision") if isinstance(data, dict) else None)


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
    clips = clips_of(current)
    start = max((_end(c) for c in clips), default=0.0)
    length = IMAGE_SECONDS if kind == "image" else _video_length(pid, rel, IMAGE_SECONDS)
    clip = {"id": new_id(), "kind": kind, "start": start, "in": 0, "out": length, "media_rel": rel, "label": rel.rsplit("/", 1)[-1]}
    tl = clean(pid, {"fps": current["fps"], "tracks": [{"id": "V1", "clips": [*clips, clip]}]}, _keep(current))
    return _write(pid, tl, current["revision"])


def from_plan(pid: str, *, replace: bool) -> dict:
    """V1 aus dem Drehbuch: Video → Videoclip, nur Bild → Standbild, sonst Platzhalter; lückenlos, in Reihenfolge.
    Die Tonspuren bleiben, wie sie sind."""
    current = load(pid)
    if clips_of(current) and not replace:
        raise plan.PlanError("studio_timeline_not_empty", 409)
    clips = clips_from_scenes(pid, plan.list_scenes(pid))
    if not clips:
        raise plan.PlanError("studio_timeline_no_shots")
    tl = clean(pid, {"fps": current["fps"], "tracks": [{"id": "V1", "clips": clips}]}, _keep(current))
    return _write(pid, tl, current["revision"])
