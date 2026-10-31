"""Gemeinsames fürs Programm: Fehler, Grenzen, Namen prüfen, Zeit."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

MAX_ITEMS = 2000          # Titel je Playlist
MAX_ADD = 500             # Titel auf einmal hinzufügen
MAX_QUEUE = 100
MAX_NAME = 80


class ProgramError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_id() -> str:
    return uuid.uuid4().hex[:16]


def clean_name(name: str) -> str:
    n = " ".join(str(name or "").split())
    if not n or len(n) > MAX_NAME:
        raise ProgramError("radiostream_name_invalid")
    return n
