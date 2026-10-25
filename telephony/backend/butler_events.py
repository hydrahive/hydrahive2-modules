"""Butler – Ereignis „Anruf kommt rein“ und Entscheidung (PLAN-BUTLER Etappe B1).

Während es klingelt, fragt der Anruf den Butler (``decide``): Die Abläufe des Verbindungs-Inhabers laufen mit dem
Ereignis ``telephony_call_incoming``; die erste Aktion mit einer Telefon-Entscheidung gewinnt. Kein Treffer, Fehler
oder Zeit abgelaufen → None (dann gelten die Einstellungen). Ein kaputter Ablauf blockiert so nie einen Anruf.
"""
from __future__ import annotations

import asyncio
import logging
import re

from hydrahive.butler.models import TriggerEvent

logger = logging.getLogger(__name__)
EVENT_INCOMING = "telephony_call_incoming"
DECIDE_SECONDS = 3.0
_PREFIX = "telephony:"                       # ActionResult.detail = "telephony:<json>" trägt die Entscheidung
_NUM_RE = re.compile(r"sip:(\+?[0-9]{3,20})@")


def normalize(number: str) -> str:
    """Nur Ziffern; +49 / 0049 → 0, + → 00. Leer, wenn es keine Rufnummer ist."""
    n = re.sub(r"[ \-/().]", "", (number or "").strip())
    if n.startswith("+"):
        n = "00" + n[1:]
    if not n.isdigit():
        return ""
    return "0" + n[4:] if n.startswith("0049") else n


def caller_number(from_header: str) -> str:
    m = _NUM_RE.search(from_header or "")
    return normalize(m.group(1)) if m else ""


def incoming_event(owner: str, cid: str, number: str) -> TriggerEvent:
    num = normalize(number)
    return TriggerEvent(event_type=EVENT_INCOMING, channel="telephone", owner=owner, contact_id=num or None,
                        payload={"number": num, "number_masked": ("•••" + num[-3:]) if len(num) >= 3 else "unbekannt",
                                 "anonymous": not num, "connection_id": cid})


def decision_result(decision: dict):
    import json

    from hydrahive.butler.registry import ActionResult

    return ActionResult(ok=True, detail=_PREFIX + json.dumps(decision, ensure_ascii=False), stop_default=True)


def decision_of(result) -> dict | None:
    import json

    detail = getattr(result, "detail", None) or (result.get("detail") if isinstance(result, dict) else None)
    if not isinstance(detail, str) or not detail.startswith(_PREFIX):
        return None
    try:
        d = json.loads(detail[len(_PREFIX):])
    except ValueError:
        return None
    return d if isinstance(d, dict) and d.get("action") in ("assistant", "greeting", "reject", "busy", "default") \
        else None


def _owner_username(cid: str) -> str | None:
    from hydrahive.api.middleware.users import get_by_id
    from hydrahive.db.connection import db

    with db() as c:
        row = c.execute("SELECT owner FROM module_telephony_connections WHERE id=?", (cid,)).fetchone()
    if not row or not str(row["owner"]).startswith("user:"):
        return None
    user = get_by_id(row["owner"][5:])
    return user["username"] if user else None


async def _dispatch(event: TriggerEvent) -> list[dict]:
    from hydrahive.butler.executor import dispatch_event
    return await dispatch_event(event, owner=event.owner)


def decide(cid: str, number: str, *, timeout: float = DECIDE_SECONDS) -> dict | None:
    """Entscheidung des ersten passenden Ablaufs oder None. Läuft im Anruf-Thread (blockierend, mit Zeitgrenze)."""
    try:
        owner = _owner_username(cid)
        if not owner:
            return None
        results = asyncio.run(asyncio.wait_for(_dispatch(incoming_event(owner, cid, number)), timeout))
    except Exception as e:  # noqa: BLE001 - Butler-Fehler dürfen den Anruf nie aufhalten
        logger.warning("telephony: Butler-Entscheidung fehlgeschlagen (%s) – Einstellungen gelten", type(e).__name__)
        return None
    for r in results:
        for a in r.get("actions_executed", []):
            d = decision_of(a)
            if d is not None:
                return d
    return None


def has_flows(cid: str) -> bool:
    """Gibt es einen eingeschalteten Ablauf mit „Anruf kommt rein“? Sonst gar nicht erst fragen (spart Zeit)."""
    from hydrahive.butler.persistence import list_flows

    owner = _owner_username(cid)
    if not owner:
        return False
    return any(f.enabled and any(n.type == "trigger" and n.subtype == "telephony_call_incoming" for n in f.nodes)
               for f in list_flows(owner=owner))
