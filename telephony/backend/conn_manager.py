"""Hält je Verbindung höchstens einen laufenden SipAgent (PLAN-EINSTELLUNGEN Schritt 5).

Prozessweit, threadsicher. ``ensure`` startet neu, wenn sich Zugangsdaten/Ports geändert haben (Fingerabdruck),
``stop`` meldet ab. Der Modul-Job ruft regelmäßig ``connections.reconcile`` auf, damit „Verbinden“ einen Neustart übersteht.
"""
from __future__ import annotations

import hashlib
import threading

from .sip.agent import SipAgent


def fingerprint(cfg: dict) -> str:
    keys = ("user", "password", "domain", "target", "bind", "display_name", "interval", "rtp_ports")
    return hashlib.sha256(repr([cfg[k] for k in keys]).encode()).hexdigest()


class Manager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._agents: dict[str, tuple[str, SipAgent]] = {}

    def running(self) -> list[str]:
        with self._lock:
            return sorted(cid for cid, (_, a) in self._agents.items() if a.alive)

    def get(self, cid: str) -> SipAgent | None:
        with self._lock:
            item = self._agents.get(cid)
        return item[1] if item else None

    def ensure(self, cid: str, cfg: dict, on_status) -> SipAgent:
        fp = fingerprint(cfg)
        with self._lock:
            item = self._agents.get(cid)
            if item and item[0] == fp and item[1].alive:
                return item[1]
            old = item[1] if item else None
        if old:
            old.stop()                                    # abmelden, Port freigeben, bevor neu gebunden wird
        agent = SipAgent(connection_id=cid, on_status=on_status, **cfg)
        with self._lock:
            self._agents[cid] = (fp, agent)
        agent.start()
        return agent

    def stop(self, cid: str) -> None:
        with self._lock:
            item = self._agents.pop(cid, None)
        if item:
            item[1].stop()

    def stop_all(self) -> None:
        with self._lock:
            items = list(self._agents.values())
            self._agents.clear()
        for _, agent in items:
            agent.stop()
