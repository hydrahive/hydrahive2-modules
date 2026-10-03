"""Hintergrundjob: Kryptex alle 5 min abrufen und in den Cache schreiben."""
from __future__ import annotations

import logging

from . import fx, kryptex, store

logger = logging.getLogger(__name__)

INTERVAL_SECONDS = 300


async def refresh() -> int:
    """Einmal abrufen. Gibt die Zahl gespeicherter Coins zurück (0 = nichts geändert)."""
    rate = await fx.fetch_usd_per_eur()
    if rate:
        store.set_usd_per_eur(rate)
    try:
        quotes = await kryptex.fetch_quotes()
    except kryptex.KryptexError as exc:
        logger.warning("Mining: Kryptex nicht erreichbar, letzte Werte bleiben: %s", exc)
        return 0
    store.replace_quotes(quotes)
    return len(quotes)


async def poll() -> None:
    await refresh()
