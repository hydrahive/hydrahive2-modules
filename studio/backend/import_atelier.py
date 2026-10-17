"""Planungsdaten aus dem Atelier übernehmen (Spec „Bauplan Etappe 2“): KOPIE, das Atelier wird nur gelesen.

Atelier-Format → Studio-Format: character_ids → element_ids, shots/<scene>.json → shots[] der Szene, Pfade der Medien
relativ zum Projekt (atelier/…), ci.json → look, film/audio/voice_model → models.
"""
from __future__ import annotations

from datetime import datetime, timezone

from . import _clean, plan
from ._store import is_id, project_root, read_json, root, write_json


def _src(pid: str):
    return project_root(pid) / "atelier"


def _scenes(pid: str) -> dict[str, dict]:
    d = _src(pid) / "screenplay" / "scenes"
    out = {}
    for f in sorted(d.glob("*.json")) if d.is_dir() else []:
        data = read_json(f, None)
        if is_id(f.stem) and isinstance(data, dict):
            out[f.stem] = data
    return out


def _shots(pid: str, scene_id: str) -> list[dict]:
    data = read_json(_src(pid) / "screenplay" / "shots" / f"{scene_id}.json", [])
    return [s for s in data if isinstance(s, dict)] if isinstance(data, list) else []


def _characters(pid: str) -> dict[str, dict]:
    d = _src(pid) / "characters"
    out = {}
    for child in sorted(d.iterdir()) if d.is_dir() else []:
        data = read_json(child / "character.json", None)
        if is_id(child.name) and isinstance(data, dict) and _clean.text(data.get("name"), 200):
            out[child.name] = data
    return out


def preview(pid: str) -> dict:
    scenes, chars = _scenes(pid), _characters(pid)
    ci = (_src(pid) / "ci.json").is_file()
    shots = sum(len(_shots(pid, s)) for s in scenes)
    return {"available": bool(scenes or chars or ci or (_src(pid) / "screenplay" / "screenplay.json").is_file()),
            "scenes": len(scenes), "shots": shots, "elements": len(chars), "look": ci, "plan_exists": plan.has_plan(pid)}


def _media(rel) -> str | None:
    return f"atelier/{rel}" if isinstance(rel, str) and rel and not rel.startswith(("/", "atelier/")) else rel or None


def run(pid: str) -> dict:
    if plan.has_plan(pid):
        raise plan.PlanError("studio_plan_exists", 409)
    info = preview(pid)
    if not info["available"]:
        raise plan.PlanError("studio_nothing_to_import", 404)
    chars = _characters(pid)
    for cid, c in chars.items():
        refs = [f"atelier/{r}" for r in (c.get("references") or []) if isinstance(r, str)]
        refs = [r for r in refs if plan.safe_rel(pid, r, plan.IMAGE_EXT)]
        write_json(root(pid, create=True) / "elements" / cid / "element.json",
                   _clean.element(cid, {**c, "kind": "character"}, refs))
    known = set(chars)
    scenes = _scenes(pid)
    shots_total = 0
    for sid, sc in scenes.items():
        shots = [{**s, "element_ids": s.get("character_ids"), "image_rel": _media(s.get("image_rel")),
                  "video_rel": _media(s.get("video_rel"))} for s in _shots(pid, sid)]
        dialogues = [{**d, "element_id": d.get("character_id")} for d in (sc.get("dialogues") or []) if isinstance(d, dict)]
        cleaned = _clean.scene(sid, {**sc, "element_ids": sc.get("character_ids"), "dialogues": dialogues}, known, shots=shots)
        shots_total += len(cleaned["shots"])
        write_json(root(pid, create=True) / "scenes" / f"{sid}.json", cleaned)
    head = read_json(_src(pid) / "screenplay" / "screenplay.json", {})
    head = head if isinstance(head, dict) else {}
    ci = read_json(_src(pid) / "ci.json", {})
    ci = ci if isinstance(ci, dict) else {}
    order = [s for s in (head.get("scene_order") or []) if s in scenes] + [s for s in scenes if s not in (head.get("scene_order") or [])]
    plan.save_head(pid, {**head, "models": {"video": head.get("film_model"), "music": head.get("audio_model"),
                                            "voice": head.get("voice_model"), "image": ci.get("default_model")},
                         "look": {"style": ci.get("style_anchor"), "palette": ci.get("palette")}}, scene_order=order)
    result = {"source": "atelier", "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "scenes": len(scenes), "shots": shots_total, "elements": len(chars), "look": bool(ci)}
    write_json(root(pid) / "imported.json", result)
    return result
