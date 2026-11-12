"""Übernahme der alten Zettel-Dateien (Scratchpad 1.x) in einzelne Ideen.

Bis 1.0.6 gab es je Nutzer zwei Freitexte: ``data_dir/scratchpad/<user>/user.md``
und ``agent.md``. Beim ersten Zugriff werden sie an Überschriften der ersten
Ebene (``# ``) geteilt. Danach heißen die Dateien ``*.md.imported`` und bleiben
liegen, damit ein Zurück auf 1.x ohne Datenverlust möglich ist.

Die ID einer Idee wird aus Nutzer, Datei, Position und Inhalt abgeleitet. Ein
zweiter Lauf über dieselbe Datei legt deshalb nichts doppelt an.
"""
from __future__ import annotations

import hashlib
import logging
import os
import sqlite3
import uuid
from pathlib import Path

from hydrahive.settings import settings

from . import store

logger = logging.getLogger(__name__)

# Datei → Herkunft. Die Datei des Nutzers kommt zuletzt, damit seine Ideen oben in der Liste stehen.
_ZONES = (("agent", "agent"), ("user", "user"))
_NAMESPACE = uuid.UUID("6f0d4c1e-5b1a-4a57-9d3e-2c8a1f7b9e40")
_FENCES = ("```", "~~~")
_RULES = ("---", "***", "___")
_PART_SUFFIX_ROOM = 12  # Platz für „ (Teil 99)“ im Titel


def _folder(username: str) -> Path | None:
    root = (settings.data_dir / "scratchpad").resolve()
    folder = (root / username).resolve()
    return folder if root in folder.parents else None


def _trim(lines: list[str]) -> list[str]:
    """Leerzeilen und Trennlinien am Anfang und Ende entfernen."""
    start, end = 0, len(lines)
    while start < end and (not lines[start].strip() or lines[start].strip() in _RULES):
        start += 1
    while end > start and (not lines[end - 1].strip() or lines[end - 1].strip() in _RULES):
        end -= 1
    return lines[start:end]


def split_sections(text: str) -> list[tuple[str | None, list[str]]]:
    """Teilt an ``# ``-Zeilen außerhalb von Codeblöcken. Der erste Eintrag ist der Text davor."""
    sections: list[tuple[str | None, list[str]]] = [(None, [])]
    fenced = False
    for line in text.splitlines():
        if line.lstrip().startswith(_FENCES):
            fenced = not fenced
        if not fenced and line.startswith("# ") and line[2:].strip():
            sections.append((line[2:].strip(), []))
        else:
            sections[-1][1].append(line)
    return sections


def _chunks(body: str, limit: int) -> list[str]:
    """Zu lange Beschreibungen an Absätzen teilen statt abschneiden."""
    if len(body) <= limit:
        return [body]
    parts: list[str] = []
    current = ""
    for paragraph in body.split("\n\n"):
        while len(paragraph) > limit:  # einzelner Absatz über der Grenze: hart teilen
            if current:
                parts.append(current)
                current = ""
            parts.append(paragraph[:limit])
            paragraph = paragraph[limit:]
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) > limit:
            parts.append(current)
            current = paragraph
        else:
            current = candidate
    if current:
        parts.append(current)
    return parts


def entries(text: str) -> list[tuple[str, str]]:
    """Datei-Inhalt → Liste aus (Kopfzeile, Beschreibung) in Lesereihenfolge."""
    result: list[tuple[str, str]] = []
    for heading, raw in split_sections(text):
        lines = _trim(raw)
        if heading is None:
            if not lines:
                continue
            heading, lines = lines[0], _trim(lines[1:])
        title = " ".join(heading.split())
        body = "\n".join(lines).rstrip()
        if len(title) > store.MAX_TITLE:  # volle Zeile bleibt in der Beschreibung erhalten
            body = f"{title}\n\n{body}".rstrip()
            title = title[: store.MAX_TITLE - 1] + "…"
        base = title[: store.MAX_TITLE - _PART_SUFFIX_ROOM]
        for number, chunk in enumerate(_chunks(body, store.MAX_BODY), start=1):
            result.append((title if number == 1 else f"{base} (Teil {number})", chunk))
    return result


def _idea_id(username: str, zone: str, index: int, title: str, body: str) -> str:
    digest = hashlib.sha256(f"{title}\n{body}".encode("utf-8")).hexdigest()
    return str(uuid.uuid5(_NAMESPACE, f"{username}\n{zone}\n{index}\n{digest}"))


def _free_name(path: Path) -> Path:
    """``user.md.imported``, bei vorhandener Datei ``user.md.imported.2`` usw."""
    target = path.with_name(path.name + ".imported")
    number = 2
    while target.exists():
        target = path.with_name(f"{path.name}.imported.{number}")
        number += 1
    return target


def _import_file(username: str, path: Path, zone: str, origin: str) -> int:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        logger.warning("scratchpad: %s nicht lesbar, Übernahme übersprungen", path.name)
        return 0
    found = entries(text)
    created = 0
    # Rückwärts anlegen: die Liste zeigt die neueste Änderung zuerst, so bleibt die Lesereihenfolge.
    for index in reversed(range(len(found))):
        title, body = found[index]
        idea_id = _idea_id(username, zone, index, title, body)
        if store.get(username, idea_id):
            continue
        try:
            store.create(username, title=title, body=body, origin=origin, idea_id=idea_id)
        except sqlite3.IntegrityError:  # ein gleichzeitiger Aufruf war schneller
            continue
        except store.IdeaError as exc:
            logger.warning("scratchpad: Übernahme von %s abgebrochen (%s), Datei bleibt liegen",
                           path.name, exc.code)
            return created
        created += 1
    try:
        os.replace(path, _free_name(path))
    except OSError:
        # Die Ideen sind angelegt. Der nächste Lauf erkennt sie an der ID und versucht es erneut.
        logger.warning("scratchpad: %s konnte nicht umbenannt werden", path.name)
    return created


def import_for(username: str) -> int:
    """Alte Dateien des Nutzers übernehmen. Liefert die Zahl neu angelegter Ideen."""
    folder = _folder(username)
    if folder is None or not folder.is_dir():
        return 0
    created = 0
    for zone, origin in _ZONES:
        path = folder / f"{zone}.md"
        if path.is_file():
            created += _import_file(username, path, zone, origin)
    return created
