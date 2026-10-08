"""Storyteller — öffentliche Ablage-API (Bücher als Dateien im Projektordner, Spec 1b §2/§3).

    storyteller/books/<id>/book.json        Kopf (Titel, Art, Sprache, …, model, version)
    storyteller/books/<id>/structure.json   Teile → Kapitel → Szenen-IDs + Steckbriefe (Reihenfolge NUR hier)
    storyteller/books/<id>/scenes/<id>.md   Szenentext (reines Markdown, für Agenten lesbar)
    storyteller/books/<id>/scenes/<id>.json Szenen-Infos inkl. version
Jede Änderung prüft die Version, auf der der Client aufbaut → ``Conflict`` statt still zu überschreiben.
"""
from __future__ import annotations

from ._book import (MAX_SCENE_BYTES, MAX_SCENES, Conflict, book_dir, books_dir, create_book,
                    delete_book, get_book, get_structure, list_books, save_structure, update_book)
from ._files import StoryError, story_root
from .scenes import add_chapter, add_scene, get_scene, remove_scene, save_scene, scene_info
from .snapshots import add_snapshot, list_snapshots

__all__ = [
    "MAX_SCENE_BYTES", "MAX_SCENES", "Conflict", "StoryError", "add_chapter",
    "add_scene", "add_snapshot", "book_dir", "books_dir", "create_book", "delete_book", "get_book", "get_scene",
    "get_structure", "list_books", "list_snapshots", "remove_scene", "save_scene", "save_structure",
    "scene_info", "story_root", "update_book",
]
