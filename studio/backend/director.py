"""Regie-Agent des Studios: zerlegt eine Szene per LLM in 2–5 Shots (Spec „Bauplan 2b“).

Vorbild: atelier/backend/director.py (gleiche Regeln). Eigene Kopie, weil das Atelier in Etappe 8 entfällt und Module
nicht übereinander importieren. Ersetzt die Shots der Szene NUR bei Erfolg; Shots mit Bild/Video nur nach Rückfrage.
"""
from __future__ import annotations

import json
import logging
import threading

from hydrahive.llm import client as llm_client

from . import plan, presets, shots
from ._clean import CAMERA_KEYS

logger = logging.getLogger("hhmod_studio.director")

MAX_SHOTS = 5
_busy: set[str] = set()                                   # Projekte mit laufender Zerlegung
_busy_lock = threading.Lock()                             # Thread-Lock: auch Sammelaufträge (eigene Loop) zerlegen

SYSTEM_PROMPT = (
    "You are a professional film director and cinematographer. You break a scene down into a sequence of concrete "
    "camera shots for AI video generation. Reply ONLY with a JSON array, no prose, no markdown fences. Each element:\n"
    '{"shot": "<one of the allowed shot keys>", '
    '"prompt": "<a vivid, self-contained ENGLISH video-generation prompt for this shot>", '
    '"element_ids": ["<ids of characters/places/objects visible in this shot>"], '
    '"duration": <seconds, integer 3-10>}\n'
    "Rules: 2-5 shots per scene. Vary the shot types for good rhythm (establishing -> medium -> close). The prompt "
    "must fully describe what is seen (setting, characters by their described looks, action, lighting, mood) so a "
    "video model needs no extra context. Keep continuity of looks. Use only the given ids."
)


def scene_context(pid: str, scene: dict) -> str:
    """Lesbarer Kontext für das LLM: Szene, Look des Drehbuchs, Bausteine der Szene, Dialoge, erlaubte Shot-Arten."""
    head = plan.get_head(pid)
    lines = [f"SCENE: {scene.get('title') or '(untitled)'}"]
    for label, key in (("Description", "description"), ("Location", "location"), ("Time of day", "time_of_day")):
        if scene.get(key):
            lines.append(f"{label}: {scene[key]}")
    cam = scene.get("camera") or {}
    phrases = [presets.phrase_for(g, cam[g]) for g in CAMERA_KEYS if cam.get(g)]
    if any(phrases):
        lines.append("Requested look: " + ", ".join(p for p in phrases if p))
    if head["look"]["style"]:
        lines.append(f"Overall style of the film: {head['look']['style']}")
    allowed = shots.scene_elements(pid, scene)
    cast = [e for e in plan.list_elements(pid) if e["id"] in allowed]
    if cast:
        lines.append("Elements in this scene (use their ids in element_ids):")
        for e in cast:
            look = " ".join(x for x in (e.get("description"), e.get("style_anchor")) if x)
            lines.append(f'- id={e["id"]} kind={e["kind"]} name="{e["name"]}" look="{look}"')
    names = {e["id"]: e["name"] for e in cast}
    dialogues = [d for d in scene.get("dialogues") or [] if isinstance(d, dict) and d.get("line")]
    if dialogues:
        lines.append("Dialogue (for pacing and emotion, do not render text on screen):")
        for d in dialogues:
            who = names.get(d.get("element_id"), "narrator")
            lines.append(f'  {who}: "{d["line"]}"' + (f" ({d['emotion']})" if d.get("emotion") else ""))
    lines.append("Allowed shot keys: " + ", ".join(presets.GROUPS["shot"]))
    return "\n".join(lines)


def parse_answer(raw: str) -> list[dict]:
    """JSON-Array aus der Antwort holen; toleriert ```json-Zäune und Text davor/danach. Unbrauchbares → []."""
    text = (raw or "").strip()
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end <= start:
        return []
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return []
    return [d for d in data if isinstance(d, dict)] if isinstance(data, list) else []


def _has_media(scene: dict) -> bool:
    return any(isinstance(s, dict) and (s.get("image_rel") or s.get("video_rel")) for s in scene.get("shots") or [])


async def decompose(pid: str, scene_id: str, *, replace: bool = False) -> list[dict]:
    scene = shots.load_scene(pid, scene_id)                # 404 vor allem anderen
    if _has_media(scene) and not replace:
        raise plan.PlanError("studio_decompose_has_media", 409)
    with _busy_lock:
        if pid in _busy:
            raise plan.PlanError("studio_decompose_busy", 409)
        _busy.add(pid)
    try:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": scene_context(pid, scene)}]
        model = plan.get_head(pid)["models"]["text"] or None
        try:
            raw = await llm_client.complete(messages, model=model, temperature=0.7, max_tokens=2000)
        except Exception as e:
            logger.warning("Studio-Regie: LLM-Fehler (Projekt %s, Szene %s): %s", pid, scene_id, e)
            raise plan.PlanError("studio_decompose_failed", 502) from e
        items = parse_answer(raw)[:MAX_SHOTS]
        if not items:
            logger.warning("Studio-Regie: unbrauchbare Antwort (Projekt %s, Szene %s)", pid, scene_id)
            raise plan.PlanError("studio_decompose_failed", 502)
        fresh = [{k: it.get(k) for k in shots.EDITABLE} | {"status": "planned"} for it in items]
        return shots.save_shots(pid, shots.load_scene(pid, scene_id), fresh)
    finally:
        _busy.discard(pid)
