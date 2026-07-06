"""Atelier — Regie: Drehbuch-Kopf + Szenen (dateibasiert im Projekt-Workspace).

Ein **Screenplay** je Projekt bündelt Titel, Beschreibung, Film-/Audio-Modell
und die geordnete Szenen-Liste. Eine **Szene** trägt Beschreibung, mitspielende
Charaktere, Dialoge, Musik-Untermalung und Kamera-Presets.

Persistenz analog ``characters.py``:
    screenplay/screenplay.json      Kopf (inkl. scene_order = einzige Reihenfolge-Quelle)
    screenplay/scenes/<id>.json     je Szene

``scene_order`` lebt ausschließlich im Kopf — die Szenen-Dateien tragen KEINE
Reihenfolge (kein Split-Brain). E1: kein Akt, kein Shot, kein Agent.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from . import storage

# Bekannte Kamera-Preset-Gruppen (Werte werden nicht gegen den Katalog geprüft,
# nur die Gruppen-Keys — der Preset-Katalog lebt in presets.py/CameraControls).
_CAMERA_KEYS = ("shot", "lens", "light", "weather", "time", "mood")


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


def _head_path(project_id: str):
    return storage.screenplay_dir(project_id) / "screenplay.json"


def _scene_path(project_id: str, scene_id: str):
    return storage.scenes_dir(project_id) / f"{scene_id}.json"


# ---- Kopf -------------------------------------------------------------------

_DEFAULT_HEAD = {
    "title": "",
    "logline": "",
    "description": "",
    "film_model": "",
    "audio_model": "",
    "voice_model": "",
    "aspect_ratio": "16:9",
    "default_duration": 5,
    "scene_order": [],
}


def get_screenplay(project_id: str) -> dict:
    head = _read_json(_head_path(project_id), None)
    if not isinstance(head, dict):
        head = dict(_DEFAULT_HEAD)
    for k, v in _DEFAULT_HEAD.items():
        head.setdefault(k, v.copy() if isinstance(v, list) else v)
    # scene_order robust auf existierende Szenen einschränken
    head["scene_order"] = [s for s in head["scene_order"] if storage.is_valid_id(s)]
    return head


def _clamp_int(value: Any, lo: int, hi: int, default: int) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, n))


def _sanitize_head(data: dict, *, scene_order: list[str]) -> dict:
    return {
        "title": str(data.get("title") or "")[:200],
        "logline": str(data.get("logline") or "")[:500],
        "description": str(data.get("description") or "")[:4000],
        "film_model": str(data.get("film_model") or "")[:200],
        "audio_model": str(data.get("audio_model") or "")[:200],
        "voice_model": str(data.get("voice_model") or "")[:200],
        "aspect_ratio": str(data.get("aspect_ratio") or "16:9")[:16],
        "default_duration": _clamp_int(data.get("default_duration"), 1, 60, 5),
        "scene_order": [s for s in scene_order if storage.is_valid_id(s)],
    }


def save_screenplay(project_id: str, data: dict) -> dict:
    """Speichert den Kopf. ``scene_order`` wird — falls im Payload gesetzt —
    übernommen, sonst die bestehende Reihenfolge beibehalten (Kopf-Edit ohne
    Reorder darf die Szenen nicht durcheinanderwerfen)."""
    current = get_screenplay(project_id)
    order = data.get("scene_order")
    if not isinstance(order, list):
        order = current["scene_order"]
    head = _sanitize_head(data, scene_order=order)
    head["created_at"] = current.get("created_at") or _now()
    head["updated_at"] = _now()
    _write_json(_head_path(project_id), head)
    return head


# ---- Szenen -----------------------------------------------------------------

def _sanitize_dialogue(raw: Any) -> dict | None:
    if not isinstance(raw, dict):
        return None
    line = str(raw.get("line") or "")[:2000]
    if not line:
        return None
    return {
        "character_id": str(raw.get("character_id") or "")[:32],
        "line": line,
        "emotion": str(raw.get("emotion") or "")[:50],
    }


def _sanitize_music(raw: Any) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    return {
        "enabled": bool(raw.get("enabled")),
        "prompt": str(raw.get("prompt") or "")[:1000],
        "music_rel": (str(raw["music_rel"])[:400]
                      if isinstance(raw.get("music_rel"), str) else None),
    }


def _sanitize_camera(raw: Any) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    return {k: str(raw[k])[:60] for k in _CAMERA_KEYS if raw.get(k)}


def _sanitize_scene(scene_id: str, data: dict) -> dict:
    dialogues = [d for d in (_sanitize_dialogue(x) for x in (data.get("dialogues") or [])) if d][:100]
    char_ids = [str(c)[:32] for c in (data.get("character_ids") or []) if str(c).strip()][:32]
    return {
        "id": scene_id,
        "title": str(data.get("title") or "")[:200],
        "description": str(data.get("description") or "")[:4000],
        "character_ids": char_ids,
        "dialogues": dialogues,
        "music": _sanitize_music(data.get("music")),
        "camera": _sanitize_camera(data.get("camera")),
        "location": str(data.get("location") or "")[:200],
        "time_of_day": str(data.get("time_of_day") or "")[:50],
    }


def get_scene(project_id: str, scene_id: str) -> dict | None:
    if not storage.is_valid_id(scene_id):
        return None
    data = _read_json(_scene_path(project_id, scene_id), None)
    return data if isinstance(data, dict) else None


def list_scenes(project_id: str) -> list[dict]:
    """Szenen in ``scene_order``-Reihenfolge. Verwaiste Order-Einträge werden
    übersprungen; auf der Platte vorhandene, aber nicht gelistete Szenen ans Ende."""
    order = get_screenplay(project_id)["scene_order"]
    seen: set[str] = set()
    out: list[dict] = []
    for sid in order:
        sc = get_scene(project_id, sid)
        if sc and sid not in seen:
            out.append(sc)
            seen.add(sid)
    sdir = storage.scenes_dir(project_id)
    for child in sorted(sdir.glob("*.json")) if sdir.is_dir() else []:
        sid = child.stem
        if sid not in seen:
            sc = get_scene(project_id, sid)
            if sc:
                out.append(sc)
                seen.add(sid)
    return out


def create_scene(project_id: str, data: dict) -> dict:
    scene_id = storage.new_id()
    scene = _sanitize_scene(scene_id, data)
    now = _now()
    scene["created_at"] = now
    scene["updated_at"] = now
    _write_json(_scene_path(project_id, scene_id), scene)
    head = get_screenplay(project_id)
    head["scene_order"] = [*head["scene_order"], scene_id]
    save_screenplay(project_id, head)
    return scene


def update_scene(project_id: str, scene_id: str, data: dict) -> dict | None:
    existing = get_scene(project_id, scene_id)
    if existing is None:
        return None
    merged = {**existing, **data}
    scene = _sanitize_scene(scene_id, merged)
    scene["created_at"] = existing.get("created_at") or _now()
    scene["updated_at"] = _now()
    _write_json(_scene_path(project_id, scene_id), scene)
    return scene


def delete_scene(project_id: str, scene_id: str) -> bool:
    if not storage.is_valid_id(scene_id):
        return False
    path = _scene_path(project_id, scene_id)
    if not path.is_file():
        return False
    path.unlink(missing_ok=True)
    head = get_screenplay(project_id)
    head["scene_order"] = [s for s in head["scene_order"] if s != scene_id]
    save_screenplay(project_id, head)
    return True


def reorder_scenes(project_id: str, ordered_ids: list[str]) -> dict:
    """Setzt die Szenen-Reihenfolge robust gegen Client-Drift:
    unbekannte IDs raus, fehlende (aber existierende) Szenen ans Ende."""
    existing = {s["id"] for s in list_scenes(project_id)}
    seen: set[str] = set()
    new_order: list[str] = []
    for sid in ordered_ids or []:
        if sid in existing and sid not in seen:
            new_order.append(sid)
            seen.add(sid)
    for sid in (s["id"] for s in list_scenes(project_id)):
        if sid not in seen:
            new_order.append(sid)
            seen.add(sid)
    head = get_screenplay(project_id)
    head["scene_order"] = new_order
    return save_screenplay(project_id, head)
