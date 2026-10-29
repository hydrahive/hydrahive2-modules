"""Nächtliches Einlesen: stündlicher Job; startet um 4 Uhr (Ortszeit), wenn heute noch keiner lief.

Das allererste Einlesen startet nur per Knopf (SPEC) – danach hält sich die Bibliothek selbst aktuell.
Ein angefangenes, aber nie fertig gewordenes Einlesen (z. B. Server-Neustart mittendrin) gilt als angefangen:
Es wird nachts nachgeholt, und ein in der DB hängen gebliebenes „scanning“ wird beim ersten Job-Lauf als
abgebrochen markiert (Befund Hauptserver 29.10.2026).
"""
from __future__ import annotations

from datetime import datetime, timezone

from . import scan_state, scanner, settings_store

HOUR = 4
INTERRUPTED = "radiostream_scan_interrupted"


def _now() -> datetime:
    return datetime.now().astimezone()


def recover_interrupted() -> bool:
    """DB sagt „scanning“, aber in diesem Prozess läuft keiner → war ein Abbruch. True, wenn aufgeräumt."""
    src = settings_store.get()
    if not src or src["state"] != "scanning" or scan_state.snapshot()["running"]:
        return False
    settings_store.mark("error", error=INTERRUPTED)
    return True


def due(now: datetime | None = None) -> bool:
    now = now or _now()
    src = settings_store.get()
    if not src or now.hour != HOUR or scan_state.snapshot()["running"]:
        return False
    if not src["last_scan_finished"]:
        return bool(src["last_scan_started"])            # angefangen, nie fertig → nachholen
    last = datetime.strptime(src["last_scan_finished"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return last.astimezone(now.tzinfo).date() < now.date()


async def tick() -> None:
    recover_interrupted()
    if due(_now()):
        scanner.start_in_background()
