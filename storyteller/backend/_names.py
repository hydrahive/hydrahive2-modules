"""Buchart, Sprache und Standardnamen für neue Teile/Kapitel/Szenen (gleich wie frontend/bookFactory.ts)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

KINDS = ("novel", "story", "nonfiction", "learning")
LANGUAGES = ("de", "en")
KIND_LABEL = {"novel": "Roman", "story": "Geschichte", "nonfiction": "Sachbuch", "learning": "Lernbuch"}
LANGUAGE_LABEL = {"de": "Deutsch", "en": "Englisch"}


def is_fiction(kind: str) -> bool:
    return kind in ("novel", "story")


@dataclass(frozen=True)
class DefaultNames:
    part: str
    chapter: Callable[[int], str]
    scene: Callable[[int], str]


def default_names(kind: str, language: str) -> DefaultNames:
    en = language.lower().startswith("en")
    fiction = is_fiction(kind)
    return DefaultNames(
        part=("Part 1" if fiction else "Contents") if en else ("Teil 1" if fiction else "Inhalt"),
        chapter=lambda n: f"Chapter {n}" if en else f"Kapitel {n}",
        scene=lambda n: (f"Scene {n}" if fiction else f"Section {n}") if en else (f"Szene {n}" if fiction else f"Abschnitt {n}"),
    )
