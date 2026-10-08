"""Knöpfe im Reiter „Team“ (T1e, Plan schreib-team-t1e.md): ein Klick beauftragt genau einen Helfer ohne Chat.

Recherche und Kreativ haben bewusst keinen Knopf – sie brauchen eine Frage bzw. Richtung (dafür ist der Chat da).
``out_tokens`` ist die Pauschale für die Kostenschätzung (Antwort + abgelegte Hinweise/Vorschläge).
"""
from __future__ import annotations

from dataclasses import dataclass

from .._files import StoryError


@dataclass(frozen=True)
class Job:
    key: str
    role: str          # Schlüssel der Rolle in team.HELPERS
    scope: str         # "scene" | "chapter"
    label: str
    goal: str          # was der Helfer tun soll
    deliver: str       # wie er das Ergebnis ablegt
    out_tokens: int


_NOTE_HINT = "Lege jeden Befund mit `storyteller_note` als Hinweis (kind „hint“) ab, Stelle: {place_key} = {place_id}."

JOBS: tuple[Job, ...] = (
    Job("check_scene", "plausibility", "scene", "Szene prüfen",
        "Prüfe die Szene gegen Steckbriefe, frühere Szenen und Zeitlinie auf Widersprüche.", _NOTE_HINT, 3000),
    Job("edit_scene", "editor", "scene", "Lektorat",
        "Lektoriere die Szene: Stil, Wiederholungen, Lesbarkeit, KI-Floskeln.",
        "Lege eine überarbeitete Fassung mit `storyteller_propose_text` als Vorschlag ab (scene_id = {place_id}) "
        "und begründe die wichtigsten Änderungen kurz mit `storyteller_note` (kind „hint“, {place_key} = {place_id}).",
        8000),
    Job("critique_chapter", "critic", "chapter", "Kritisch lesen",
        "Lies das Kapitel kritisch: Lücken in Handlung und Logik, schwache Spannung, unklare Motive.", _NOTE_HINT, 4000),
    Job("structure_chapter", "structure", "chapter", "Aufbau prüfen",
        "Prüfe Aufbau und Tempo des Kapitels: Reihenfolge der Szenen, Spannungsbogen, Längen.", _NOTE_HINT, 4000),
    Job("update_profiles", "profiles", "scene", "Steckbriefe pflegen",
        "Suche in der Szene neue Fakten über Figuren, Orte und Gegenstände.",
        "Lege neue oder ergänzte Steckbriefe mit `storyteller_propose_entity` als Vorschlag ab. "
        "Widersprüche zu vorhandenen Steckbriefen als Hinweis mit `storyteller_note` ({place_key} = {place_id}).",
        3000),
)
_BY_KEY = {j.key: j for j in JOBS}


def get(key: str) -> Job:
    job = _BY_KEY.get(key)
    if job is None:
        raise StoryError("job_unknown")
    return job


def task_text(job: Job, *, book_id: str, book_title: str, place_id: str, place_title: str) -> str:
    """Auftrag an den Helfer. Titel stehen nur im f-String (werden nicht weiter ersetzt, „{…}“ darin bleibt wörtlich)."""
    place_key = "scene_id" if job.scope == "scene" else "chapter_id"
    where = "Szene" if job.scope == "scene" else "Kapitel"
    deliver = job.deliver.replace("{place_key}", place_key).replace("{place_id}", place_id)
    return (f"Auftrag aus dem Reiter „Team“ (ohne Chat, niemand liest deine Antwort mit – nur was du ablegst, zählt).\n"
            f"Buch: {book_title} (book_id {book_id}). {where}: „{place_title}“ ({place_key} {place_id}).\n\n"
            f"{job.goal}\nLies dazu zuerst mit `storyteller_read` bzw. `storyteller_outline`.\n{deliver}\n"
            "Kein Fund → nichts ablegen. Zum Schluss eine kurze Zusammenfassung in 1–3 Sätzen.")
