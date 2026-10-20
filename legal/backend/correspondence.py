"""Schriftverkehr einer Fallakte (Plan L3 Schritt 4, Spec §4.2/§4.7). Rechte prüfen Route bzw. Werkzeug.

Eingang (`in`, Status `received`): der Mensch schreibt ab bzw. fasst zusammen (Upload/OCR erst L5).
Ausgang (`out`): Entwurf (`draft`) → „versendet am … per …“ (`sent`). **Kein automatischer Versand.** Versendete
Schreiben sind nicht mehr änderbar (Beweisstand).
"""
from __future__ import annotations

import json
from datetime import date
from typing import Any

from hydrahive.db.connection import db

from .casefile import _case, _text
from .cases import CaseError, _now
from .letter_check import DELIVERY

_COLS = ("id", "project_id", "direction", "status", "date", "sender", "recipient", "their_ref", "our_ref", "subject",
         "body", "delivery", "proof", "letter_type", "attachments", "created_by", "created_at", "updated_at")
_LIMITS = {"sender": 500, "recipient": 500, "their_ref": 100, "our_ref": 100, "subject": 300, "body": 50000,
           "proof": 200, "letter_type": 40}
_EDITABLE = set(_LIMITS) | {"date", "delivery", "attachments"}


def _date(v: Any, *, required: bool) -> str:
    s = str(v or "").strip()
    if not s:
        if required:
            raise CaseError("date_required")
        return ""
    try:
        return date.fromisoformat(s).isoformat()
    except ValueError:
        raise CaseError("date_invalid") from None


def _clean(fields: dict[str, Any], *, partial: bool) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, limit in _LIMITS.items():
        if key in fields or not partial:
            out[key] = _text(fields.get(key), key, limit)
    if "date" in fields or not partial:
        out["date"] = _date(fields.get("date"), required=False)
    if "delivery" in fields or not partial:
        d = str(fields.get("delivery") or "")
        if d and d not in DELIVERY:
            raise CaseError("delivery_invalid", allowed=list(DELIVERY))
        out["delivery"] = d
    if "attachments" in fields or not partial:
        att = fields.get("attachments", [])
        if not isinstance(att, list) or len(att) > 30:
            raise CaseError("attachments_invalid")
        out["attachments"] = json.dumps([_text(a, "attachment", 300) for a in att if str(a or "").strip()],
                                        ensure_ascii=False)
    return out


def _row(row: tuple) -> dict[str, Any]:
    e = dict(zip(_COLS, row, strict=True))
    e["attachments"] = json.loads(e["attachments"])
    return e


def _get(project_id: str, entry_id: int) -> dict[str, Any]:
    with db() as c:
        row = c.execute(f"SELECT {', '.join(_COLS)} FROM module_legal_correspondence WHERE id = ? AND project_id = ?",
                        (entry_id, project_id)).fetchone()
    if row is None:
        raise CaseError("correspondence_not_found", 404)
    return _row(row)


def add(project_id: str, fields: dict[str, Any], *, by: str) -> dict[str, Any]:
    _case(project_id)
    direction = fields.get("direction")
    if direction not in ("in", "out"):
        raise CaseError("direction_invalid", allowed=["in", "out"])
    data = _clean(fields, partial=False)
    if direction == "in" and not data["date"]:
        raise CaseError("date_required")
    status = "received" if direction == "in" else "draft"
    now = _now()
    cols = ("project_id", "direction", "status", *data, "created_by", "created_at", "updated_at")
    vals = (project_id, direction, status, *data.values(), by[:200], now, now)
    with db() as c:
        cur = c.execute(f"INSERT INTO module_legal_correspondence({', '.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                        vals)
        new_id = cur.lastrowid
    return _get(project_id, new_id)


def list_for(project_id: str) -> list[dict[str, Any]]:
    with db() as c:
        rows = c.execute(f"SELECT {', '.join(_COLS)} FROM module_legal_correspondence WHERE project_id = ? "
                         "ORDER BY CASE WHEN date = '' THEN created_at ELSE date END DESC, id DESC", (project_id,)).fetchall()
    return [_row(r) for r in rows]


def update(project_id: str, entry_id: int, fields: dict[str, Any]) -> dict[str, Any]:
    e = _get(project_id, entry_id)
    if e["status"] == "sent":
        raise CaseError("correspondence_sent_locked", 409)
    unknown = set(fields) - _EDITABLE
    if unknown:
        raise CaseError("field_unknown", fields=sorted(unknown))
    data = _clean(fields, partial=True)
    if not data:
        raise CaseError("nothing_to_update")
    sets = ", ".join(f"{k} = ?" for k in data)
    with db() as c:
        c.execute(f"UPDATE module_legal_correspondence SET {sets}, updated_at = ? WHERE id = ? AND project_id = ?",
                  (*data.values(), _now(), entry_id, project_id))
    return _get(project_id, entry_id)


def mark_sent(project_id: str, entry_id: int, fields: dict[str, Any]) -> dict[str, Any]:
    e = _get(project_id, entry_id)
    if e["direction"] != "out":
        raise CaseError("correspondence_not_outgoing", 409)
    sent_date = _date(fields.get("date"), required=True)
    delivery = str(fields.get("delivery") or "")
    if delivery not in DELIVERY:
        raise CaseError("delivery_invalid", allowed=list(DELIVERY))
    proof = _text(fields.get("proof"), "proof", 200)
    with db() as c:
        c.execute("UPDATE module_legal_correspondence SET status = 'sent', date = ?, delivery = ?, proof = ?, "
                  "updated_at = ? WHERE id = ? AND project_id = ?", (sent_date, delivery, proof, _now(), entry_id,
                                                                     project_id))
    return _get(project_id, entry_id)


def delete(project_id: str, entry_id: int) -> None:
    e = _get(project_id, entry_id)
    if e["status"] == "sent":
        raise CaseError("correspondence_sent_locked", 409)
    with db() as c:
        c.execute("DELETE FROM module_legal_correspondence WHERE id = ? AND project_id = ?", (entry_id, project_id))
