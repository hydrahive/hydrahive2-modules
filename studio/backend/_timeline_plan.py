"""Schnittfassung aus dem Drehbuch bauen (Spec „Bauplan Etappe 4“, 4a „Aus dem Drehbuch übernehmen“)."""
from __future__ import annotations

import math

from ._sources import IMAGE_EXT, VIDEO_EXT
from ._store import new_id, project_root, read_json, safe_rel


def _video_length(pid: str, rel: str, fallback: float) -> float:
    """Länge aus der Begleitdatei des Videos (schreibt 3b mit), sonst die Dauer des Shots."""
    meta = read_json(project_root(pid) / f"{rel}.json", {})
    d = meta.get("duration") if isinstance(meta, dict) else None
    if isinstance(d, (int, float)) and not isinstance(d, bool) and math.isfinite(d) and d > 0:
        return float(d)
    return fallback


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
