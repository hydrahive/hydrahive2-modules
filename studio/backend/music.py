"""Musik erzeugen (Spec „Nachtrag 5c-2“): Beschreibung → Tondatei unter studio/media/music/. Auf die Zeitleiste legt sie
der Browser (nur ein Ort schreibt die Schnittfassung). Höchstens ein Musikauftrag je Projekt."""
from __future__ import annotations

import math
from datetime import datetime, timezone

from . import _clean, jobs, music_provider, plan, shots
from ._store import new_id, root, write_json
from .speech import probe_seconds

MEDIA_DIR = "studio/media/music"
MIN_SECONDS, MAX_SECONDS = 5, 180


def _seconds(v) -> int:
    if not isinstance(v, (int, float)) or not math.isfinite(v) or not MIN_SECONDS <= v <= MAX_SECONDS:
        raise plan.PlanError("studio_music_invalid")
    return round(v)


def prompt_for(description: str, seconds: int) -> str:
    return f"{description.rstrip('. ')}. Instrumental, about {seconds} seconds long."


def _work(pid: str, description: str, seconds: int, scene_id: str, model: str) -> dict:
    prompt = prompt_for(description, seconds)
    try:
        data = music_provider.generate(prompt, model)
    except music_provider.ProviderError as e:
        raise jobs.JobFailed(str(e)) from e
    name = f"{new_id()}.mp3"
    target = root(pid, create=True) / "media" / "music" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    duration = probe_seconds(target)
    if duration is None:
        target.unlink(missing_ok=True)
        raise jobs.JobFailed("bad_audio")
    meta = {"description": description, "prompt": prompt, "model": model, "duration": duration, "seconds": seconds,
            "scene_id": scene_id, "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    write_json(target.with_name(name + ".json"), meta)
    return {"rel": f"{MEDIA_DIR}/{name}", "duration": duration, "seconds": seconds, "scene_id": scene_id, "model": model}


def start(pid: str, data: dict) -> dict:
    data = data if isinstance(data, dict) else {}
    description = _clean.text(data.get("description"), 2000)
    if not description:
        raise plan.PlanError("studio_music_needs_text")
    seconds = _seconds(data.get("seconds"))
    scene_id = data.get("scene_id") or ""
    if scene_id:
        shots.load_scene(pid, scene_id)                                   # 404, wenn es die Szene nicht gibt
    model = plan.get_head(pid)["models"]["music"] or music_provider.server_default_model()
    return jobs.start(pid, "music", f"music:{pid}", scene_id, lambda: _work(pid, description, seconds, scene_id, model),
                      busy_code="studio_music_running")


def _shot_seconds(scene: dict) -> int:
    return int(sum(float(s.get("duration") or 0) for s in scene.get("shots") or [] if isinstance(s, dict)))


def defaults(pid: str) -> dict:
    """Vorbelegung des Formulars: Beschreibung aus Logline + Look bzw. der Szene, Länge = Summe der Shots."""
    head = plan.get_head(pid)
    scenes = plan.list_scenes(pid)
    film_text = ". ".join(x for x in (head.get("logline", ""), head["look"]["style"]) if x)
    film_seconds = sum(_shot_seconds(s) for s in scenes)
    fit = lambda n: max(MIN_SECONDS, min(MAX_SECONDS, n or 30))
    return {
        "model": head["models"]["music"] or music_provider.server_default_model(),
        "film": {"description": film_text, "seconds": fit(film_seconds)},
        "scenes": [{"id": s["id"], "title": s.get("title") or "", "description": s.get("description") or "", "seconds": fit(_shot_seconds(s))}
                   for s in scenes],
    }
