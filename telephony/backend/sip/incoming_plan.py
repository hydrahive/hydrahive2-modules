"""Butler-Entscheidung im Anruf umsetzen (PLAN-BUTLER B1) – läuft im Anruf-Thread nach „180 Ringing“.

``apply`` fragt den Butler (``dispatcher.decide``) und stellt den Anruf ein: ablehnen (480), besetzt (486), Ansage
(eigener Text oder Einstellungen) oder Assistent (eigenes Wissen/Name oder Einstellungen). „Wie in den Einstellungen“,
kein Treffer oder Fehler → bisherige Regel (Schalter + Modus). Rückgabe: (Code, Grund, Ergebnis) zum Abweisen, sonst None.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .call import CallSession
    from .dispatch import CallDispatcher

logger = logging.getLogger(__name__)
FALLBACK_GREETING = "Hallo, hier ist HydraHive. Im Moment ist leider niemand erreichbar. Auf Wiederhören."
REJECT = (480, "Temporarily Unavailable", "rejected")
BUSY = (486, "Busy Here", "busy")


def _safe(fn, *args):
    try:
        return fn(*args)
    except Exception:
        logger.warning("telephony: Anruf-Entscheidung – Teil fehlgeschlagen", exc_info=True)
        return None


def _greeting(d: CallDispatcher, s: CallSession, text: str) -> None:
    s._audio = lambda: d._greeting(text, s.codec)


def prepare(d: CallDispatcher, s: CallSession, number: str) -> bool:
    """Im Anruf-Thread nach 180: True = Anruf erledigt (abgelehnt/besetzt oder währenddessen aufgelegt)."""
    final = apply(d, s, number)
    if final is not None and not s._ended.is_set():
        s.respond(final[0], final[1])
        s._end(final[2])
    return s._ended.is_set()


def apply(d: CallDispatcher, s: CallSession, number: str) -> tuple[int, str, str] | None:
    from .dispatch import mask_number

    decision = _safe(d.decide, number) or {}
    action = decision.get("action", "default")
    if action == "reject":
        return REJECT
    if action == "busy":
        return BUSY
    if action == "default":
        text = _safe(d.policy)
        if text is None:
            return REJECT
        _greeting(d, s, text)
        s._assistant = d._assistant_for(s.invite)
        return None
    if action == "assistant":
        a = _safe(d.assistant_settings)
        if a is not None:
            if decision.get("knowledge"):
                a["cfg"].knowledge = decision["knowledge"]
            if decision.get("name"):
                a["cfg"].owner_name = decision["name"]
            a["cfg"].caller_number = mask_number(s.invite.header("from") or "")
            s._assistant = a
            return None
    _greeting(d, s, decision.get("text") or _safe(d.greeting_text) or FALLBACK_GREETING)
    return None
