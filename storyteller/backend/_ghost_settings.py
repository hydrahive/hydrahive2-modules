"""Ghostwriter-Einstellungen je Buch (book.json: ghost) und Herkunft je Szene (origin).

Kein festes Modell und keine festen Werte im Code (Till, 06.10.2026): Leer bzw. 0 heißt
„nicht gesetzt“; dann greift das Buchmodell bzw. der HydraHive-Standard bzw. die Auswahl in
der Oberfläche.
"""
from __future__ import annotations

from typing import Any

from ._files import StoryError

GHOST_DEFAULTS: dict[str, Any] = {"model": "", "length_words": 0, "chunk_words": 0, "style": "", "limit_tokens": 0}
# limit_tokens: Kostengrenze je Auftrag in Tokens, Eingabe + Ausgabe (Spec kostengrenze.md §3), 0 = aus.
# Gilt für Ghostwriter-Läufe, „Szene schreiben“ und Team-Aufträge.
_RANGES = {"length_words": (200, 6000), "chunk_words": (200, 2000), "limit_tokens": (1000, 20_000_000)}
_TEXT_LIMITS = {"model": 200, "style": 2000}

ORIGINS = ("human", "ai_draft", "ai_edited")


def valid_limit(value: Any) -> int:
    """Kostengrenze prüfen (0 = aus, sonst im Bereich) – auch für die Grenze am Team-Auftrag."""
    low, high = _RANGES["limit_tokens"]
    if isinstance(value, bool) or not isinstance(value, int) or (value != 0 and not low <= value <= high):
        raise StoryError("limit_invalid")
    return value


def ghost_of(book: dict) -> dict:
    """Einstellungen mit Standardwerten (ältere Bücher haben das Feld nicht)."""
    return {**GHOST_DEFAULTS, **(book.get("ghost") or {})}


def merge_ghost(current: dict, patch: Any) -> dict:
    """Teil-Änderung prüfen und auf den bisherigen Stand anwenden."""
    if not isinstance(patch, dict) or set(patch) - set(GHOST_DEFAULTS):
        raise StoryError("ghost_invalid")
    out = dict(current)
    for key, value in patch.items():
        if key in _TEXT_LIMITS:
            if not isinstance(value, str) or len(value) > _TEXT_LIMITS[key]:
                raise StoryError("ghost_invalid")
        elif key == "limit_tokens":
            try:
                valid_limit(value)
            except StoryError:
                raise StoryError("ghost_invalid") from None
        else:
            low, high = _RANGES[key]
            if isinstance(value, bool) or not isinstance(value, int) or (value != 0 and not low <= value <= high):
                raise StoryError("ghost_invalid")
        out[key] = value
    return out


def next_origin(current: str, data: dict[str, Any], text_changed: bool) -> str:
    """Herkunft nach dem Speichern: ausdrücklich gesetzt (z. B. Ghostwriter → ai_draft) oder
    KI-Entwurf, dessen Text ein Mensch ändert → ai_edited."""
    if "origin" in data:
        if data["origin"] not in ORIGINS:
            raise StoryError("origin_invalid")
        return data["origin"]
    if current == "ai_draft" and text_changed:
        return "ai_edited"
    return current
