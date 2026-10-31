"""Vorgeladenen Titel verwerfen, wenn sich Warteschlange oder Programm ändern (PLAN-PROGRAMM.md „Als Nächstes“).

Liquidsoap lädt einen Titel vor (prefetch=1). Das Steuer-Kommando `autodj.flush` wirft ihn weg und nennt seine
Spiel-Kennung (rs_play, aus /feed/next). Hier wird er zurückgenommen:
- Eintrag in der Gespielt-Liste weg (sonst wären Künstler/Titel gesperrt, obwohl nichts lief),
- kam er aus der Warteschlange: wieder vorn hinein,
- kam er aus der aktuell gewählten Playlist: Stelle zurück (der Reihe nach) bzw. wieder offen (gemischt).
Fehlt der Sender oder antwortet er nicht, passiert nichts – nie ein Fehler nach außen.
"""
from __future__ import annotations

import logging
import re
import threading
from collections.abc import Iterator
from contextlib import contextmanager

from . import control, program, queue_store, rotation

logger = logging.getLogger(__name__)
_ID = re.compile(r"^\d{1,12}$")
# Zurücknehmen + Änderung + nächste Auswahl dürfen sich nicht überholen: Liquidsoap fragt direkt nach dem Verwerfen
# neu an (/feed/next, eigener Thread). Die Anfrage wartet, bis die Änderung gespeichert ist.
LOCK = threading.RLock()


def _send(cmd: str) -> str:
    return control._send(cmd)


def _running() -> bool:
    return control.status()["running"]


def _restore(origin: dict) -> None:
    if origin["source"] == "queue":
        queue_store.enqueue(origin["track_id"], user="system", front=True)
        return
    if origin["source"] != "playlist":
        return
    pid, mode, pos = (origin["ref"].split(":") + ["", "", ""])[:3]
    prog = program.get_program()
    if prog["mode"] != "playlist" or prog["ref_id"] != pid or not pos.isdigit():
        return                                            # inzwischen anderes Programm: nichts verstellen
    if mode == "ordered":
        program.save_position(cursor=int(pos))
    else:
        program.save_position(played=[p for p in prog["played"] if p != int(pos)])


def flush() -> None:
    try:
        if not _running():
            return
        answer = _send("autodj.flush")
    except (OSError, control.ControlError):
        logger.info("Radiostream: vorgeladenen Titel nicht verworfen (Sender antwortet nicht)")
        return
    first = (answer or "").replace("\r", "").split("\n", 1)[0]
    for raw in first.split(","):
        raw = raw.strip()
        if not _ID.match(raw):
            continue
        origin = rotation.play_origin(int(raw))
        if origin is None:
            continue
        rotation.unrecord(int(raw))
        try:
            _restore(origin)
        except program.ProgramError:
            logger.info("Radiostream: vorgeladenen Titel nicht zurückgestellt (Warteschlange voll oder Titel weg)")


@contextmanager
def changing() -> Iterator[None]:
    """Für jede Programm-Änderung: erst den vorgeladenen Titel zurücknehmen, dann ändern – alles unter der Sperre."""
    with LOCK:
        flush()
        yield


def locked_next() -> dict:
    """Nächsten Titel wählen und eintragen (für /feed/next) – wartet auf eine laufende Änderung."""
    from . import choose
    with LOCK:
        t = choose.next_track()
        t["play_id"] = rotation.record(t["track_id"], t["artist"], album_artist=t.get("album_artist", ""),
                                       source=t.get("source", ""), ref=t.get("ref", ""))
    return t
