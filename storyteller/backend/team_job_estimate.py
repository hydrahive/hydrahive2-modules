"""Kostenschätzung vor dem Start eines Team-Auftrags (T1e). Grob, aber nachvollziehbar:

Eingabe ≈ (Text der Szene bzw. aller Szenen des Kapitels + Steckbriefe + Gliederung) / 4 Zeichen je Token, mal
``READS`` (der Helfer liest in mehreren Werkzeug-Runden, jede Runde schickt den Verlauf erneut) plus Anweisung.
Ausgabe = Pauschale des Knopfs. Preise nur aus dem Kern; unbekanntes Modell → keine Euro-Angabe (``None``).
Die tatsächlichen Kosten stehen nach dem Lauf am Auftrag.
"""
from __future__ import annotations

import json

from . import scenes, storage
from ._cost import cost_micros, tokens
from ._files import StoryError
from .team.jobs_catalog import Job

READS = 3           # Werkzeug-Runden, in denen das Gelesene im Verlauf mitläuft
PROMPT_TOKENS = 4000  # Anweisung des Helfers + Werkzeugbeschreibungen


def place(project_id: str, book_id: str, job: Job, place_id: str) -> tuple[str, list[str]]:
    """(Titel, Szenen-IDs) der Stelle; die Stelle muss zum Bereich des Knopfs passen."""
    st = storage.get_structure(project_id, book_id)
    for c in (c for p in st["parts"] for c in p["chapters"]):
        if job.scope == "chapter" and c["id"] == place_id:
            return c["title"], list(c["scenes"])
        if job.scope == "scene" and place_id in c["scenes"]:
            return scenes.get_scene(project_id, book_id, place_id)["title"], [place_id]
    raise StoryError("place_not_found", 404)


def estimate(project_id: str, book_id: str, job: Job, place_id: str, *, model: str) -> dict:
    title, scene_ids = place(project_id, book_id, job, place_id)
    st = storage.get_structure(project_id, book_id)
    text = sum(tokens(scenes.get_scene(project_id, book_id, s)["text"]) for s in scene_ids)
    context = tokens(json.dumps(st.get("entities", []), ensure_ascii=False)) + tokens(json.dumps(st["parts"]))
    tin, tout = PROMPT_TOKENS + READS * (text + context), job.out_tokens
    return {"job": job.key, "place_id": place_id, "place_title": title, "model": model, "input_tokens": tin,
            "output_tokens": tout, "cost_micros": cost_micros(model, tokens_in=tin, tokens_out=tout)}
