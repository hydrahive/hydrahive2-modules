"""Eröffnung bei ausgehenden Anrufen (PLAN-ANRUFEN-3, 3b): Gegenseite meldet sich zuerst, dann stellt sich der
Assistent vor und nennt von sich aus den Grund.

Ausgelagert aus ``conversation.py`` (Dateigröße). Liefert, was die Gegenseite beim Abheben gesagt hat (oder einen
festen Platzhalter, wenn nichts zu hören war) – das geht als erste Gegenseiten-Nachricht an das Modell.
"""
from __future__ import annotations

import queue
import time
from typing import TYPE_CHECKING

from ..media import g711

if TYPE_CHECKING:
    from .conversation import Conversation

OPENING_SILENT = "(hat abgenommen, aber noch nichts gesagt)"


def hello(conv: Conversation, wait_first: float) -> str | None:
    """Höchstens ``wait_first`` s auf den Beginn einer Meldung warten; hat sie begonnen, bis zu ihrem Ende.

    None = aufgelegt. Der Ton wird sofort nach der Erkennung verworfen.
    """
    end = time.monotonic() + wait_first
    while True:
        if conv._hangup():
            return None
        if not conv.vad.in_speech and time.monotonic() >= end:
            return OPENING_SILENT
        if conv._over():
            return OPENING_SILENT
        try:
            f = conv._frames.get(timeout=0.05)
        except queue.Empty:
            continue
        if f is None:
            return None
        for e in conv.vad.feed(f):
            if e.kind == "utterance":
                try:
                    text = conv._stt(g711.up_16k(e.pcm)).strip()
                except Exception:  # noqa: BLE001 - nicht verstanden ist kein Abbruch
                    text = ""
                return text or OPENING_SILENT
