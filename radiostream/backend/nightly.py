"""Nächtliches Einlesen: stündlicher Job; startet um 4 Uhr (Ortszeit), wenn heute noch keiner lief.

Das allererste Einlesen startet nur per Knopf (SPEC) – danach hält sich die Bibliothek selbst aktuell.
"""
from __future__ import annotations

from datetime import datetime, timezone

from . import scan_state, scanner, settings_store

HOUR = 4


def due(now: datetime | None = None) -> bool:
    now = (now or datetime.now().astimezone())
    src = settings_store.get()
    if not src or not src["last_scan_finished"] or now.hour != HOUR or scan_state.snapshot()["running"]:
        return False
    last = datetime.strptime(src["last_scan_finished"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return last.astimezone(now.tzinfo).date() < now.date()


async def tick() -> None:
    if due():
        scanner.start_in_background()
