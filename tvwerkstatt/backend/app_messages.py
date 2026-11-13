"""HydraHive-App (G1): Ereignisse vom Gerät und Einblendungen an das Gerät.

Ereignisse: feste Arten (an/aus, App vorne, Eingang, Wiedergabe, Knopf einer Einblendung), Daten als kleines JSON
(≤ 2 KB), je Gerät höchstens 500 – Älteres wird gekappt. Einblendungen: Titel ≤ 80, Text ≤ 300, ≤ 3 Knöpfe zu je
≤ 20 Zeichen; die App holt sie ab (lange Abfrage), meldet „gezeigt“ und optional die Antwort.
"""
from __future__ import annotations

import asyncio
import json
import time

from hydrahive.db.connection import db

from .app_pairing import AppError, _iso, _now

EVENT_KINDS = ("screen", "foreground", "input", "playback", "answer", "hello")
MAX_EVENT = 2000
KEEP_EVENTS = 500
KEEP_NOTICES = 200
POLL_STEP = 1.0


def _text(v, limit: int) -> str:
    s = " ".join(str(v if isinstance(v, (str, int, float)) and not isinstance(v, bool) else "").split())
    return "".join(ch for ch in s if ord(ch) >= 32 and ord(ch) != 127)[:limit]


def add_event(app_id: str, kind: str, data: dict) -> None:
    if kind not in EVENT_KINDS:
        raise AppError("tvw_app_bad_event")
    raw = json.dumps(data if isinstance(data, dict) else {}, separators=(",", ":"), ensure_ascii=False)
    if len(raw) > MAX_EVENT:
        raise AppError("tvw_app_event_too_large")
    with db() as conn:
        conn.execute("INSERT INTO module_tvwerkstatt_app_events (app_id, kind, data) VALUES (?, ?, ?)",
                     (app_id, kind, raw))
        conn.execute("DELETE FROM module_tvwerkstatt_app_events WHERE app_id = ? AND event_id NOT IN (SELECT event_id "
                     "FROM module_tvwerkstatt_app_events WHERE app_id = ? ORDER BY event_id DESC LIMIT ?)",
                     (app_id, app_id, KEEP_EVENTS))
        conn.commit()


def events(app_id: str, limit: int = 30) -> list[dict]:
    with db() as conn:
        rows = conn.execute("SELECT event_id, kind, data, created_at FROM module_tvwerkstatt_app_events "
                            "WHERE app_id = ? ORDER BY event_id DESC LIMIT ?",
                            (app_id, max(1, min(limit, 200)))).fetchall()
    return [{"event_id": r[0], "kind": r[1], "data": json.loads(r[2] or "{}"), "created_at": r[3]} for r in rows]


def clean_notice(title: str, body: str, buttons: list) -> tuple[str, str, list[str]]:
    t, b = _text(title, 80), _text(body, 300)
    if not t:
        raise AppError("tvw_app_bad_notice")
    btns = [x for x in (_text(v, 20) for v in (buttons or [])[:3]) if x] if isinstance(buttons, list) else []
    return t, b, btns


def send(app_id: str, title: str, body: str, buttons: list, created_by: str) -> int:
    t, b, btns = clean_notice(title, body, buttons)
    with db() as conn:
        if not conn.execute("SELECT 1 FROM module_tvwerkstatt_app_devices WHERE app_id = ? AND status = 'active'",
                            (app_id,)).fetchone():
            raise AppError("tvw_app_not_found")
        cur = conn.execute("INSERT INTO module_tvwerkstatt_app_notices (app_id, title, body, buttons, created_by) "
                           "VALUES (?, ?, ?, ?, ?)", (app_id, t, b, json.dumps(btns, ensure_ascii=False), created_by))
        conn.execute("DELETE FROM module_tvwerkstatt_app_notices WHERE app_id = ? AND notice_id NOT IN "
                     "(SELECT notice_id FROM module_tvwerkstatt_app_notices WHERE app_id = ? "
                     "ORDER BY notice_id DESC LIMIT ?)",
                     (app_id, app_id, KEEP_NOTICES))
        conn.commit()
        return int(cur.lastrowid)


def pending(app_id: str, after: int) -> list[dict]:
    with db() as conn:
        rows = conn.execute("SELECT notice_id, title, body, buttons, created_at FROM module_tvwerkstatt_app_notices "
                            "WHERE app_id = ? AND notice_id > ? AND delivered_at = '' ORDER BY notice_id LIMIT 10",
                            (app_id, max(0, int(after)))).fetchall()
    return [{"notice_id": r[0], "title": r[1], "body": r[2], "buttons": json.loads(r[3] or "[]"), "created_at": r[4]}
            for r in rows]


async def wait_pending(app_id: str, after: int, seconds: float) -> list[dict]:
    """Lange Abfrage: bis eine Einblendung da ist oder die Zeit um ist (höchstens 30 s)."""
    end = time.monotonic() + max(0.0, min(seconds, 30.0))
    while True:
        got = await asyncio.to_thread(pending, app_id, after)
        if got or time.monotonic() >= end:
            return got
        await asyncio.sleep(POLL_STEP)


def mark(app_id: str, notice_id: int, *, answer: str | None = None) -> None:
    """Als gezeigt markieren; mit Antwort: Knopf muss einer der angebotenen sein."""
    with db() as conn:
        r = conn.execute("SELECT buttons FROM module_tvwerkstatt_app_notices WHERE app_id = ? AND notice_id = ?",
                         (app_id, int(notice_id))).fetchone()
        if r is None:
            raise AppError("tvw_app_notice_not_found")
        now = _iso(_now())
        if answer is None:
            conn.execute("UPDATE module_tvwerkstatt_app_notices SET delivered_at = ? WHERE notice_id = ? "
                         "AND delivered_at = ''", (now, int(notice_id)))
        else:
            if answer not in json.loads(r[0] or "[]"):
                raise AppError("tvw_app_bad_answer")
            conn.execute("UPDATE module_tvwerkstatt_app_notices SET answer = ?, answered_at = ?, "
                         "delivered_at = CASE WHEN delivered_at = '' THEN ? ELSE delivered_at END WHERE notice_id = ?",
                         (answer, now, now, int(notice_id)))
        conn.commit()


def notices(app_id: str, limit: int = 20) -> list[dict]:
    with db() as conn:
        rows = conn.execute("SELECT notice_id, title, body, buttons, answer, created_at, delivered_at, answered_at "
                            "FROM module_tvwerkstatt_app_notices WHERE app_id = ? ORDER BY notice_id DESC LIMIT ?",
                            (app_id, max(1, min(limit, 100)))).fetchall()
    keys = ("notice_id", "title", "body", "buttons", "answer", "created_at", "delivered_at", "answered_at")
    return [{**dict(zip(keys, r, strict=True)), "buttons": json.loads(r[3] or "[]")} for r in rows]
