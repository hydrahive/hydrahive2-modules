"""Anrufen per Knopf (PLAN-ANRUFEN-3 Sicherheit + Schritt 4): Nummer prüfen, Grenzen, wählen, Status, auflegen.

Nur der Eigentümer der Verbindung (Route mit ``require_principal``) kann wählen – kein Agenten-Werkzeug, kein Auslösen
durch Anrufer oder Modelltext. Die volle Zielnummer lebt nur im laufenden Anruf; gespeichert wird sie maskiert.
"""
from __future__ import annotations

import threading
import time
from datetime import UTC, datetime

from hydrahive.db.connection import db

from . import calls, connections, dialrules

MAX_PER_DAY = 20
MIN_GAP_SECONDS = 5
MAX_TEXT = 500
_LOCK = threading.Lock()
_ACTIVE: dict[str, object] = {}                 # Verbindung → laufender/letzter ausgehender Anruf
_LAST_DIAL: dict[str, float] = {}


class NotReady(RuntimeError):
    pass


class Busy(RuntimeError):
    pass


class Limit(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _now() -> float:
    return time.time()


def _agent(cid: str):
    return connections.MANAGER.get(cid)


def _render(text: str, codec: str) -> bytes:
    from .media import greeting
    return greeting.render(text, codec)


def default_text(row) -> str:
    who = (row["assistant_name"] or "").strip() or "HydraHive"
    return (f"Hallo, hier ist der digitale Assistent von {who}. Ich bin eine KI. Dies ist ein automatischer Anruf. "
            "Auf Wiederhören.")


def _today_count(cid: str) -> int:
    start = datetime.fromtimestamp(_now(), UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    with db() as c:
        return c.execute("SELECT COUNT(*) FROM module_telephony_calls WHERE connection_id=? AND direction='out' "
                         "AND started_at >= ?", (cid, start.isoformat())).fetchone()[0]


def _row(user_id: str):
    row = connections._row(connections._owner(user_id))
    if not row:
        raise calls.NotFound(user_id)
    return row


def set_rules(user_id: str, allow_premium: bool, allow_foreign: bool) -> dict:
    cid = _row(user_id)["id"]
    with db() as c:
        c.execute("UPDATE module_telephony_connections SET allow_premium=?, allow_foreign=? WHERE id=?",
                  (int(allow_premium), int(allow_foreign), cid))
    return {"allow_premium": allow_premium, "allow_foreign": allow_foreign}


def dial(user_id: str, number: str, text: str) -> dict:
    row = _row(user_id)
    cid = row["id"]
    target = dialrules.check(number, allow_premium=bool(row["allow_premium"]),
                             allow_foreign=bool(row["allow_foreign"]))
    spoken = text.strip() or default_text(row)
    agent = _agent(cid)
    if agent is None or getattr(agent, "status", "") != "registered":
        raise NotReady(getattr(agent, "status", "disconnected"))
    with _LOCK:
        if _now() - _LAST_DIAL.get(cid, 0.0) < MIN_GAP_SECONDS:
            raise Limit("too_fast")
        if _today_count(cid) >= MAX_PER_DAY:
            raise Limit("daily_limit")
        from .sip.agent import LineBusy
        from .sip.agent import NotReady as AgentNotReady

        try:
            call = agent.dial(target, lambda codec: _render(spoken, codec))
        except LineBusy:
            raise Busy() from None
        except AgentNotReady:
            raise NotReady("not_registered") from None
        _LAST_DIAL[cid] = _now()
        _ACTIVE[cid] = call
    return status(user_id)


def _public(call) -> dict:
    return {"active": bool(call.alive), "state": call.state, "number": dialrules.mask(call.number),
            "result": call.result if not call.alive else ""}


def status(user_id: str) -> dict:
    try:
        cid = _row(user_id)["id"]
    except calls.NotFound:
        return {"active": False}
    call = _ACTIVE.get(cid)
    return _public(call) if call is not None else {"active": False}


def hangup(user_id: str) -> dict:
    try:
        cid = _row(user_id)["id"]
    except calls.NotFound:
        return {"active": False}
    call = _ACTIVE.get(cid)
    if call is None or not call.alive:
        return {"active": False}
    call.hangup()
    return _public(call)
