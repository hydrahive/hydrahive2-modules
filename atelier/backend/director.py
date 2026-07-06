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
from typing import Any

from hydrahive.llm import client as llm_client

from . import characters as chars
from . import presets, screenplay, storage

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
