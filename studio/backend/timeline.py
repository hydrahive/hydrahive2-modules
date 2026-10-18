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

from . import _timeline_load, _timeline_plan, mix, plan
from ._sources import AUDIO_EXT, IMAGE_EXT, VIDEO_EXT
from ._store import is_id, new_id, read_json, root, safe_rel, write_json
from ._timeline_plan import _video_length

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


def _tracks(clips: dict[str, list[dict]], values: dict[str, dict] | None = None) -> list[dict]:
    """Spuren in fester Reihenfolge; `values`: Mischpult-Werte je Spur (nur Abweichungen vom Standard)."""
    return [{"id": tid, "kind": kind, **(values or {}).get(tid, {}), "clips": clips.get(tid, [])} for tid, kind in TRACKS]


def _with_duck(tl: dict, duck: bool) -> dict:
    return {**tl, "duck": False} if not duck else tl


def empty() -> dict:
    return {"revision": 0, "fps": FPS_DEFAULT, "tracks": _tracks({})}


def with_default_duck(tl: dict) -> dict:
    """Antwort an den Browser: `duck` immer ausgeschrieben (in der Datei nur `false`)."""
    return {**tl, "duck": tl.get("duck", True) is not False}


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
    if kind == "audio":
        try:
            out.update(mix.clip_values(raw, t_out - t_in, strict=not on_load))
        except mix.Bad as e:
            raise Invalid() from e
    return out


def clean(pid: str, data: Any, keep: dict[str, dict] | None = None) -> dict:
    """Prüft eine Fassung vollständig; wirft Invalid bei jeder Verletzung. `keep`: gespeicherte Spuren (Clips und
    Mischpult-Werte) für Spuren, die in `data` fehlen – sie werden wie neue geprüft. Fehlt `duck`, gilt der gespeicherte
    Wert bzw. der Standard."""
    if not isinstance(data, dict):
        raise Invalid()
    tracks = data.get("tracks")
    if not isinstance(tracks, list) or not 1 <= len(tracks) <= len(TRACKS) or not all(isinstance(t, dict) for t in tracks):
        raise Invalid()
    ids = [t.get("id", "V1") for t in tracks]                         # ohne id: V1 (Fassungen aus 4a/4b)
    if len(set(ids)) != len(ids) or "V1" not in ids or any(i not in dict(TRACKS) for i in ids):
        raise Invalid()
    keep = keep or {}
    full = {**{k: v for k, v in keep.items() if k != "_duck"}, **dict(zip(ids, tracks))}
    given = {i: t.get("clips") for i, t in full.items()}
    try:
        values = {i: mix.track_values(t, strict=True) for i, t in full.items()}
        duck = mix.flag(data["duck"]) if "duck" in data else keep.get("_duck", True)
    except mix.Bad as e:
        raise Invalid() from e
    out: dict[str, list[dict]] = {}
    for tid, kind in TRACKS:
        raw = given.get(tid, [])
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
    return _with_duck({"fps": fps, "tracks": _tracks(out, values)}, duck)


def _end(c: dict) -> float:
    return c["start"] + c["out"] - c["in"]


def load(pid: str) -> dict:
    """Gespeicherte Fassung oder leer (nichts wird angelegt); Einzelheiten in _timeline_load.from_file."""
    raw = read_json(_path(pid), None)
    return _timeline_load.from_file(pid, raw) if isinstance(raw, dict) else empty()


def clips_of(tl: dict, track: str = "V1") -> list[dict]:
    return next((t["clips"] for t in tl["tracks"] if t["id"] == track), [])


def all_clips(tl: dict) -> list[dict]:
    return [c for t in tl["tracks"] for c in t["clips"]]


def _keep(tl: dict) -> dict[str, dict]:
    """Gespeicherter Stand je Spur (Clips + Mischpult-Werte) und `duck` – für Spuren, die beim Speichern fehlen."""
    return {**{t["id"]: t for t in tl["tracks"]}, "_duck": tl.get("duck", True) is not False}


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
    """V1 aus dem Drehbuch (Einzelheiten in _timeline_plan.build); die Musik bleibt, gebundene Sprache wird neu gelegt."""
    current = load(pid)
    if clips_of(current) and not replace:
        raise plan.PlanError("studio_timeline_not_empty", 409)
    tracks = _timeline_plan.build(pid, current)
    tl = clean(pid, {"fps": current["fps"], "tracks": tracks}, _keep(current))
    return _write(pid, tl, current["revision"])
