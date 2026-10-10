"""Verteiler: welche Brille gehört zu welchem Nutzer, Ereignisse zustellen.

Alles nur im Speicher. Pro Nutzer bis zu MAX_CONNECTIONS Verbindungen,
jede mit eigener begrenzter Queue. Ein Ereignis geht an ALLE Brillen des
Nutzers — und nur an die.
"""
from __future__ import annotations

import asyncio
import json
import logging

logger = logging.getLogger(__name__)

MAX_CONNECTIONS = 4
QUEUE_SIZE = 50


class TooManyConnections(RuntimeError):
    """Nutzer hat schon MAX_CONNECTIONS offene Brillen-Verbindungen."""


class Hub:
    def __init__(self) -> None:
        self._subs: dict[str, list[asyncio.Queue[str]]] = {}

    def subscribe(self, user: str) -> asyncio.Queue[str]:
        subs = self._subs.setdefault(user, [])
        if len(subs) >= MAX_CONNECTIONS:
            raise TooManyConnections(user)
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=QUEUE_SIZE)
        subs.append(q)
        logger.info("VR: Brille verbunden (Nutzer %s, %d offen)", user, len(subs))
        return q

    def unsubscribe(self, user: str, q: asyncio.Queue[str]) -> None:
        subs = self._subs.get(user, [])
        if q in subs:
            subs.remove(q)
        if not subs:
            self._subs.pop(user, None)
        logger.info("VR: Brille getrennt (Nutzer %s)", user)

    def connected(self, user: str) -> int:
        return len(self._subs.get(user, []))

    def publish(self, user: str, event: dict) -> int:
        """Stellt [event] allen Brillen von [user] zu. Liefert die Anzahl Empfänger."""
        payload = json.dumps(event, ensure_ascii=False)
        subs = self._subs.get(user, [])
        for q in subs:
            if q.full():  # älteste verwerfen statt zu blockieren
                q.get_nowait()
            q.put_nowait(payload)
        return len(subs)


hub = Hub()
