"""Schnittfassung aus dem Drehbuch bauen (Spec „Bauplan Etappe 4“, 4a „Aus dem Drehbuch übernehmen“)."""
from __future__ import annotations

import math

from ._sources import AUDIO_EXT, IMAGE_EXT, VIDEO_EXT
from ._store import new_id, project_root, read_json, safe_rel


def _video_length(pid: str, rel: str, fallback: float) -> float:
    """Länge aus der Begleitdatei des Videos (schreibt 3b mit), sonst die Dauer des Shots."""
    meta = read_json(project_root(pid) / f"{rel}.json", {})
    d = meta.get("duration") if isinstance(meta, dict) else None
    if isinstance(d, (int, float)) and not isinstance(d, bool) and math.isfinite(d) and d > 0:
        return float(d)
    return fallback


def _sound_length(pid: str, rel: str) -> float:
    meta = read_json(project_root(pid) / f"{rel}.json", {})
    d = meta.get("duration") if isinstance(meta, dict) else None
    return float(d) if isinstance(d, (int, float)) and not isinstance(d, bool) and math.isfinite(d) and d > 0 else 0.0


def voice_from_scenes(pid: str, scenes: list[dict], pictures: list[dict]) -> list[dict]:
    """Sprache je Shot an den Anfang seines Bildclips (Spec 5c: an den Shot gebunden, `shot_id` gesetzt), höchstens so
    lang wie der Bildclip."""
    start = {c["shot_id"]: c for c in pictures if c.get("shot_id")}
    out = []
    for scene in scenes:
        for s in scene.get("shots") or []:
            rel = safe_rel(pid, s.get("voice_rel"), AUDIO_EXT)
            pic = start.get(s.get("id"))
            length = _sound_length(pid, rel) if rel else 0.0
            if not rel or not pic or length <= 0:
                continue
            out.append({"id": new_id(), "kind": "audio", "start": pic["start"], "in": 0,
                        "out": round(min(length, pic["out"] - pic["in"]), 3), "media_rel": rel, "scene_id": scene["id"],
                        "shot_id": s["id"], "label": (s.get("speech") or "").strip()[:80] or pic["label"]})
    return out


def clips_from_scenes(pid: str, scenes: list[dict]) -> list[dict]:
    clips, t = [], 0.0
    for n, scene in enumerate(scenes, start=1):
        title = scene.get("title") or f"#{n}"
        for i, shot in enumerate(scene.get("shots") or [], start=1):
            duration = float(shot.get("duration") or 1)
            video = safe_rel(pid, shot.get("video_rel"), VIDEO_EXT)
            image = safe_rel(pid, shot.get("image_rel"), IMAGE_EXT)
            if video:
                kind, media, length = "video", video, _video_length(pid, video, duration)
            elif image:
                kind, media, length = "image", image, duration
            else:
                kind, media, length = "placeholder", "", duration
            clips.append({"id": new_id(), "kind": kind, "start": t, "in": 0, "out": length, "media_rel": media,
                          "scene_id": scene["id"], "shot_id": shot["id"], "label": f"{title} · Shot {i}"})
            t += length
    return clips


def build(pid: str, current: dict) -> list[dict]:
    """Spuren V1 und A1 aus dem Drehbuch: Bildclips lückenlos, Sprache je Shot am Anfang ihres Bildclips. Freie
    Sprachclips (ohne `shot_id`) bleiben, sofern sie die gebundene Sprache nicht überlappen."""
    from . import plan
    from .timeline import EPS, clips_of
    scenes = plan.list_scenes(pid)
    clips = clips_from_scenes(pid, scenes)
    if not clips:
        raise plan.PlanError("studio_timeline_no_shots")
    bound = voice_from_scenes(pid, scenes, clips)
    end = lambda c: c["start"] + c["out"] - c["in"]
    free = [c for c in clips_of(current, "A1") if not c.get("shot_id")
            and all(c["start"] >= end(b) - EPS or end(c) <= b["start"] + EPS for b in bound)]
    old = next((t for t in current["tracks"] if t["id"] == "A1"), {"id": "A1"})
    return [{"id": "V1", "clips": clips}, {**old, "clips": [*bound, *free]}]
