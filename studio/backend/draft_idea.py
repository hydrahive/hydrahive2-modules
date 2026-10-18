"""Drehbuch-Entwurf aus einer Idee (Spec „Bauplan B2“): ein KI-Aufruf, Ergebnis nur als Vorschau, nichts gespeichert.

Muster wie der Regie-Agent (director.py): Text-Modell aus dem Drehbuch-Kopf, sonst das Standardmodell des Servers.
"""
from __future__ import annotations

import json
import logging

from hydrahive.llm import client as llm_client

from . import _draft, plan, presets
from ._clean import text

logger = logging.getLogger("hhmod_studio.draft_idea")

LENGTHS = ("30", "60", "120")                 # Sekunden; die Oberfläche zeigt „30 s“, „1 min“, „2 min“
MAX_IDEA, MAX_STYLE = 2000, 300
MAX_SCENES = 8
SHOT_SECONDS = (3, 10)

SYSTEM_PROMPT = (
    "You are a screenwriter and film director. From a short idea you write a compact screenplay for a short "
    "AI-generated film. Reply ONLY with one JSON object, no prose, no markdown fences:\n"
    '{"title": "...", "logline": "...", '
    '"elements": [{"key": "<short unique id>", "kind": "character|place|object", "name": "...", '
    '"description": "<visual look in ENGLISH>"}], '
    '"scenes": [{"title": "...", "description": "...", "location": "...", "time_of_day": "...", '
    '"element_keys": ["<keys of elements in this scene>"], '
    '"shots": [{"shot": "<one of the allowed shot keys>", "prompt": "<vivid, self-contained ENGLISH video prompt>", '
    '"element_keys": ["..."], "duration": <seconds, integer 3-10>}]}]}\n'
    "Rules: 2-8 scenes, 2-5 shots per scene, the sum of all shot durations close to the target length. Title, "
    "logline, scene texts and names in the language of the idea. Prompts in English; each prompt fully describes what "
    "is seen (setting, characters by their looks, action, light, mood) so a video model needs no extra context. Keep "
    "looks consistent across shots. Use only element keys you defined."
)


def _context(idea: str, length: str, style: str) -> str:
    lines = [f"IDEA: {idea}", f"Target length of the whole film: about {length} seconds"]
    if style:
        lines.append(f"Style of the film: {style}")
    lines.append("Allowed shot keys: " + ", ".join(presets.GROUPS["shot"]))
    return "\n".join(lines)


def parse_answer(raw: str) -> dict | None:
    """JSON-Objekt aus der Antwort; toleriert Zäune und Text davor/danach. Unbrauchbar → None."""
    t = (raw or "").strip()
    start, end = t.find("{"), t.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        data = json.loads(t[start:end + 1])
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _check(data: dict) -> tuple[str, str, str]:
    idea, length, style = data.get("idea"), str(data.get("length") or ""), data.get("style") or ""
    if not isinstance(idea, str) or not idea.strip() or len(idea) > MAX_IDEA or length not in LENGTHS \
            or not isinstance(style, str) or len(style) > MAX_STYLE:
        raise plan.PlanError("studio_idea_invalid")
    return idea.strip(), length, style.strip()


async def draft(pid: str, data: dict) -> dict:
    idea, length, style = _check(data)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": _context(idea, length, style)}]
    model = plan.get_head(pid)["models"]["text"] or None
    try:
        raw = await llm_client.complete(messages, model=model, temperature=0.8, max_tokens=8000)
    except Exception as e:
        logger.warning("Studio-Idee: LLM-Fehler (Projekt %s): %s", pid, e)
        raise plan.PlanError("studio_idea_failed", 502) from e
    answer = parse_answer(raw)
    try:
        if answer is None:
            raise _draft.DraftInvalid("answer")
        head = {"title": answer.get("title"), "logline": answer.get("logline"), "style": style or answer.get("style")}
        out = _draft.clean({**answer, "head": head}, strict=False, max_scenes=MAX_SCENES, durations=SHOT_SECONDS)
    except _draft.DraftInvalid as e:
        logger.warning("Studio-Idee: unbrauchbare Antwort (Projekt %s): %s", pid, text(raw, 200))
        raise plan.PlanError("studio_idea_failed", 502) from e
    return {"draft": out}
