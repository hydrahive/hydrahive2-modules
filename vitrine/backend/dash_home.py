"""Bereich „Zuhause“ der Statuszentrale (S4): Home-Assistant-Favoriten je Raum, nur lesen.

Die Vitrine hat keinen eigenen HA-Zugang. Sie liest die Favoriten des Besitzers aus der Tabelle des HA-Moduls und fragt die
Werte über dessen Client (`hhmod_homeassistant.client.render_template`) mit **einem** festen Template ab. Eingesetzt
werden nur Entity-IDs, die vorher gegen ein enges Muster geprüft wurden (als JSON-Liste).
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import sqlite3
import sys

log = logging.getLogger(__name__)
MAX_FAVORITES, BATTERY_LOW, ROOM_LEN = 50, 20, 60
OTHER = "Sonstiges"
ERR = "Home Assistant nicht erreichbar"
_ID = re.compile(r"^[a-z_]+\.[a-z0-9_]+$")
_GONE = {"unavailable", "unknown", "none", ""}
_TEMPLATE = (
    "{%- set ns = namespace(out=[]) -%}{%- for e in IDS -%}{%- set s = states[e] -%}"
    "{%- set ns.out = ns.out + [{'id': e, 'name': state_attr(e, 'friendly_name') or e, 'area': area_name(e) or '',"
    " 'dc': state_attr(e, 'device_class') or '', 'state': (s.state if s else 'unknown'),"
    " 'unit': state_attr(e, 'unit_of_measurement') or '',"
    " 'age': ((as_timestamp(now()) - as_timestamp(s.last_changed)) | int) if s else -1}] -%}"
    "{%- endfor -%}{{ ns.out | tojson }}")


def ha_client():
    mod = sys.modules.get("hhmod_homeassistant")
    return getattr(mod, "client", None) if mod is not None else None


def _hh_db():
    from hydrahive.db.connection import db
    return db()


def _favorites(username: str, connect) -> list[str] | None:
    with connect() as c:
        if c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='module_homeassistant_favorites'").fetchone() is None:
            return None
        rows = c.execute('SELECT entity_id FROM module_homeassistant_favorites WHERE "user" = ? ORDER BY sort, id',
                         (username,)).fetchall()
    return [r["entity_id"] for r in rows if _ID.fullmatch(r["entity_id"] or "")][:MAX_FAVORITES]


def _num(state: str) -> float | None:
    try:
        return float(state)
    except (TypeError, ValueError):
        return None


def _fmt(v: float, unit: str, digits: int) -> str:
    return f"{v:.{digits}f}".replace(".", ",") + (f" {unit}" if unit else "")


def _rooms(ents: list[dict], order: list[str]) -> list[dict]:
    by_room: dict[str, list[dict]] = {}
    pos = {e: i for i, e in enumerate(order)}
    for e in sorted(ents, key=lambda x: pos.get(x.get("id"), 1e9)):
        by_room.setdefault(str(e.get("area") or OTHER)[:ROOM_LEN], []).append(e)
    out = []
    for room, items in by_room.items():
        alive = [e for e in items if str(e.get("state", "")).lower() not in _GONE]
        r = {"room": room, "temp": None, "hum": None, "battery_low": None, "extra": None, "offline_h": None}
        if not alive:
            ages = [int(e.get("age", -1)) for e in items if int(e.get("age", -1)) >= 0]
            r["offline_h"] = min(ages) // 3600 if ages else 0
            out.append(r)
            continue
        for e in alive:
            v, dc, unit = _num(e.get("state")), e.get("dc"), str(e.get("unit") or "")[:8]
            if v is None:
                continue
            if dc == "temperature" and r["temp"] is None:
                r["temp"] = _fmt(v, unit, 1)
            elif dc == "humidity" and r["hum"] is None:
                r["hum"] = _fmt(v, unit, 0)
            elif dc == "battery":
                r["battery_low"] = _fmt(v, "%", 0) if v < BATTERY_LOW else r["battery_low"]
            elif r["extra"] is None:
                r["extra"] = _fmt(v, unit, 1)
        out.append(r)
    return out


def home(username: str, *, rooms: list[str], connect=_hh_db, client="auto") -> dict | None:
    """None = Bereich fehlt (HA-Modul nicht da / Tabelle fehlt). Sonst {"rooms": [...], "error": str|None}."""
    client = ha_client() if client == "auto" else client
    try:
        ids = _favorites(username, connect)
    except sqlite3.Error as e:
        log.warning("Zuhause: Favoriten nicht lesbar (%s)", type(e).__name__)
        return None
    if ids is None or client is None:
        return None
    if not ids:
        return {"rooms": [], "error": None}
    try:
        raw = asyncio.run(client.render_template(_TEMPLATE.replace("IDS", json.dumps(ids), 1)))
        ents = [e for e in json.loads(raw) if isinstance(e, dict)] if raw else []
    except Exception as e:  # noqa: BLE001 – HA-Fehler dürfen die Statuszentrale nie umwerfen
        log.warning("Zuhause: Home Assistant nicht erreichbar (%s)", type(e).__name__)
        return {"rooms": [], "error": ERR}
    result = _rooms(ents, ids)
    if rooms:
        result = [r for r in result if r["room"] in rooms]
    return {"rooms": result, "error": None}
