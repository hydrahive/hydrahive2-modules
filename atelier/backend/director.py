"""Atelier — Regieagent: zerlegt Szenen per LLM in konkrete Shots.

Phase 1 der Regie (E4): Aus einer Szene (Beschreibung, Charaktere, Dialoge,
Kamera-Wunsch) macht ein LLM eine geordnete Liste von **Shots** — je Shot eine
Kamera-Einstellung + ein präziser englischer Video-Prompt + beteiligte
Charaktere + Dauer. Es wird NICHTS generiert; die Shots landen als Vorschau
(``shots/<scene-id>.json``) mit status ``planned``. Der User prüft/editiert sie,
bevor Phase 2 (E5) sie tatsächlich rendert.

Shots liegen pro Szene in EINER Datei (Liste, Reihenfolge = Index).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from hydrahive.llm import client as llm_client

from . import characters as chars
from . import film, presets, screenplay, service, storage, video

logger = logging.getLogger("hhmod_atelier.director")

_VALID_STATUS = {"planned", "image_ready", "video_processing", "done", "failed"}
_SHOT_KEYS = list(presets.GROUPS.get("shot", {}).keys())


def _read_json(path, default: Any) -> Any:
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text("utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


def _write_json(path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _shots_path(project_id: str, scene_id: str):
    return storage.shots_dir(project_id) / f"{scene_id}.json"


# ---- Shot-Storage + CRUD ----------------------------------------------------

def _sanitize_shot(scene_id: str, order: int, data: dict) -> dict:
    shot_key = str(data.get("shot") or "")[:60]
    status = str(data.get("status") or "planned")
    if status not in _VALID_STATUS:
        status = "planned"
    try:
        duration = int(data.get("duration") or 5)
    except (TypeError, ValueError):
        duration = 5
    duration = max(1, min(60, duration))
    return {
        "id": str(data.get("id") or storage.new_id()),
        "scene_id": scene_id,
        "order": order,
        "shot": shot_key,
        "prompt": str(data.get("prompt") or "")[:2000],
        "character_ids": [str(c)[:32] for c in (data.get("character_ids") or []) if str(c).strip()][:32],
        "duration": duration,
        "status": status,
        "image_rel": data.get("image_rel") if isinstance(data.get("image_rel"), str) else None,
        "video_rel": data.get("video_rel") if isinstance(data.get("video_rel"), str) else None,
    }


def get_shots(project_id: str, scene_id: str) -> list[dict]:
    if not storage.is_valid_id(scene_id):
        return []
    data = _read_json(_shots_path(project_id, scene_id), [])
    if not isinstance(data, list):
        return []
    return [_sanitize_shot(scene_id, i, s) for i, s in enumerate(data) if isinstance(s, dict)]


def save_shots(project_id: str, scene_id: str, shots: list[dict]) -> list[dict]:
    clean = [_sanitize_shot(scene_id, i, s) for i, s in enumerate(shots) if isinstance(s, dict)]
    _write_json(_shots_path(project_id, scene_id), clean)
    return clean


def update_shot(project_id: str, scene_id: str, shot_id: str, patch: dict) -> dict | None:
    shots = get_shots(project_id, scene_id)
    found = None
    for i, s in enumerate(shots):
        if s["id"] == shot_id:
            shots[i] = _sanitize_shot(scene_id, i, {**s, **patch, "id": shot_id})
            found = shots[i]
            break
    if found is None:
        return None
    save_shots(project_id, scene_id, shots)
    return found


def delete_shot(project_id: str, scene_id: str, shot_id: str) -> bool:
    shots = get_shots(project_id, scene_id)
    remaining = [s for s in shots if s["id"] != shot_id]
    if len(remaining) == len(shots):
        return False
    save_shots(project_id, scene_id, remaining)
    return True


# ---- LLM-Zerlegung ----------------------------------------------------------

_SYSTEM_PROMPT = (
    "You are a professional film director and cinematographer. You break a scene "
    "down into a sequence of concrete camera shots for AI video generation. "
    "Reply ONLY with a JSON array, no prose, no markdown fences. Each element:\n"
    '{"shot": "<one of the allowed shot keys>", '
    '"prompt": "<a vivid, self-contained ENGLISH video-generation prompt for this shot>", '
    '"character_ids": ["<ids of characters visible in this shot>"], '
    '"duration": <seconds, integer 3-10>}\n'
    "Rules: 2-5 shots per scene. Vary the shot types for good rhythm "
    "(establishing -> medium -> close). The prompt must fully describe what is "
    "seen (setting, characters by their described looks, action, lighting, mood) "
    "so a video model needs no extra context. Keep character continuity."
)


def _scene_context(project_id: str, scene: dict) -> str:
    """Menschlich lesbarer Kontext-Block für den User-Prompt an das LLM."""
    lines = [f"SCENE: {scene.get('title') or '(untitled)'}"]
    if scene.get("description"):
        lines.append(f"Description: {scene['description']}")
    if scene.get("location"):
        lines.append(f"Location: {scene['location']}")
    if scene.get("time_of_day"):
        lines.append(f"Time of day: {scene['time_of_day']}")
    cam = scene.get("camera") or {}
    if cam:
        phrases = [presets.phrase_for(g, k) or k for g, k in cam.items()]
        lines.append("Requested look: " + ", ".join(p for p in phrases if p))
    # Charaktere mit Steckbrief + Style-Anchor (für konsistentes Aussehen)
    cast = []
    for cid in scene.get("character_ids") or []:
        c = chars.get_character(project_id, cid)
        if c:
            desc = c.get("description") or ""
            anchor = c.get("style_anchor") or ""
            cast.append(f'- id={cid} name="{c.get("name")}" look="{desc} {anchor}".strip()')
    if cast:
        lines.append("Characters in this scene (use their ids in character_ids):")
        lines.extend(cast)
    dialogues = scene.get("dialogues") or []
    if dialogues:
        lines.append("Dialogue (for pacing/emotion, do not render text on screen):")
        for d in dialogues:
            lines.append(f'  {d.get("character_id")}: "{d.get("line")}" ({d.get("emotion")})')
    lines.append(f"Allowed shot keys: {', '.join(_SHOT_KEYS)}")
    return "\n".join(lines)


def _parse_shots_json(raw: str) -> list[dict]:
    """Parst die LLM-Antwort robust — toleriert ```json-Fences und Vor-/Nachtext."""
    if not raw:
        return []
    text = raw.strip()
    # Markdown-Fences entfernen
    if text.startswith("```"):
        text = text.split("```", 2)[1] if text.count("```") >= 2 else text
        if text.lstrip().startswith("json"):
            text = text.lstrip()[4:]
    # Auf das äußere JSON-Array eingrenzen
    start, end = text.find("["), text.rfind("]")
    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    return [d for d in data if isinstance(d, dict)] if isinstance(data, list) else []


async def decompose_scene(project_id: str, scene: dict, *, model: str | None = None) -> list[dict]:
    """Zerlegt EINE Szene per LLM in Shots (status planned). Schreibt shots/<id>.json.
    Bei LLM-/Parse-Fehler: leere Liste (kein Crash)."""
    scene_id = scene["id"]
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": _scene_context(project_id, scene)},
    ]
    try:
        raw = await llm_client.complete(messages, model=model, temperature=0.7, max_tokens=2000)
    except Exception as e:  # noqa: BLE001 - LLM-Fehler nicht in den Aufrufer durchreichen
        logger.warning("decompose_scene LLM-Fehler (scene=%s): %s", scene_id, e)
        return []
    parsed = _parse_shots_json(raw)
    # gültige Charakter-IDs der Szene als Filter (LLM darf keine fremden erfinden)
    valid_ids = set(scene.get("character_ids") or [])
    shots: list[dict] = []
    for i, item in enumerate(parsed):
        item["character_ids"] = [c for c in (item.get("character_ids") or []) if c in valid_ids]
        item["status"] = "planned"
        shots.append(_sanitize_shot(scene_id, i, item))
    save_shots(project_id, scene_id, shots)
    return shots


async def decompose_all(project_id: str, *, model: str | None = None) -> dict:
    """Zerlegt alle Szenen des Drehbuchs (in scene_order). Gibt Zusammenfassung zurück."""
    scenes = screenplay.list_scenes(project_id)
    total_shots = 0
    per_scene: dict[str, int] = {}
    for scene in scenes:
        shots = await decompose_scene(project_id, scene, model=model)
        per_scene[scene["id"]] = len(shots)
        total_shots += len(shots)
    return {"scenes": len(scenes), "shots": total_shots, "per_scene": per_scene}


# ---- Batch-Render (Phase 2, E5) ---------------------------------------------

def _render_job_path(project_id: str):
    return storage.screenplay_dir(project_id) / "render.json"


def get_render_job(project_id: str) -> dict:
    return _read_json(_render_job_path(project_id), {"status": "idle"})


def _write_render_job(project_id: str, job: dict) -> None:
    _write_json(_render_job_path(project_id), job)


def _update_shot_status(project_id: str, scene_id: str, shot_id: str, patch: dict) -> None:
    shots = get_shots(project_id, scene_id)
    for i, s in enumerate(shots):
        if s["id"] == shot_id:
            shots[i] = _sanitize_shot(scene_id, i, {**s, **patch})
            break
    save_shots(project_id, scene_id, shots)


async def render_all(project_id: str, *, model: str | None = None) -> dict:
    """Rendert alle geplanten Shots: je Shot Keyframe → Clip, dann Film-Merge.

    Nutzt ausschließlich vorhandene Pfade (generate_for_project, video.render_clip,
    film.start_film_job). Fehlerhafte Shots werden übersprungen (status failed),
    der Batch läuft weiter. Schreibt Fortschritt nach render.json.
    """
    head = screenplay.get_screenplay(project_id)
    film_model = model or head.get("film_model") or ""
    aspect = head.get("aspect_ratio") or "16:9"
    scenes = screenplay.list_scenes(project_id)

    # alle geplanten (oder fehlgeschlagenen) Shots einsammeln, in Szenen-Reihenfolge
    plan: list[tuple[dict, dict]] = []  # (scene, shot)
    for scene in scenes:
        for shot in get_shots(project_id, scene["id"]):
            plan.append((scene, shot))

    job = {
        "job_id": storage.new_id(),
        "status": "processing",
        "total_shots": len(plan),
        "done_shots": 0,
        "failed_shots": 0,
        "current": "",
        "film_rel": None,
        "error": None,
        "created_at": _now(),
    }
    _write_render_job(project_id, job)

    done_clips: list[str] = []
    for scene, shot in plan:
        job["current"] = f"{scene.get('title') or 'Szene'} / shot #{shot['order'] + 1}"
        _write_render_job(project_id, job)
        try:
            # 1) Keyframe-Bild (mit Charakter-Referenzen + Kamera des Shots)
            _update_shot_status(project_id, scene["id"], shot["id"], {"status": "image_ready"})
            img = service.generate_for_project(project_id, {
                "scene": shot["prompt"],
                "character_ids": shot.get("character_ids") or [],
                "aspect_ratio": aspect,
                "camera": {"shot": shot["shot"]} if shot.get("shot") else {},
            })
            image_rel = img["rel"]
            _update_shot_status(project_id, scene["id"], shot["id"],
                                {"status": "video_processing", "image_rel": image_rel})

            # 2) Clip aus dem Keyframe
            video_rel = await video.render_clip(
                project_id, source_rel=image_rel, prompt=shot["prompt"],
                model=film_model, duration=shot.get("duration", 5), aspect_ratio=aspect,
            )
            _update_shot_status(project_id, scene["id"], shot["id"],
                                {"status": "done", "video_rel": video_rel})
            done_clips.append(video_rel)
            job["done_shots"] += 1
        except Exception as e:  # noqa: BLE001 - ein Shot-Fehler bricht den Batch nicht ab
            logger.exception("render shot failed: scene=%s shot=%s", scene["id"], shot["id"])
            _update_shot_status(project_id, scene["id"], shot["id"],
                                {"status": "failed", "error": str(e)})
            job["failed_shots"] += 1
        _write_render_job(project_id, job)

    # 3) Film aus allen fertigen Clips
    if done_clips:
        try:
            film_job = film.start_film_job(project_id, {
                "clips": done_clips, "resolution": "720p", "music_rel": "",
            })
            job["film_rel"] = film_job.get("job_id")  # Film läuft async; Job-Id zur Nachverfolgung
        except Exception as e:  # noqa: BLE001
            logger.exception("render film-merge failed")
            job["error"] = f"Film-Merge: {e}"

    job["status"] = "completed" if job["failed_shots"] == 0 else "completed_with_errors"
    job["current"] = ""
    _write_render_job(project_id, job)
    return job
