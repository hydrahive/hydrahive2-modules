"""Fallakte: Beteiligte, Fristen, Notizen (Plan L2 Schritte 4–5). Rechte prüfen Route bzw. Werkzeug.

Vorschläge des Agenten und die Gesamtsicht stehen in ``proposals.py`` (hier am Ende wieder angeboten).
"""
from __future__ import annotations

import json
from datetime import date
from typing import Any

from hydrahive.db.connection import db

from . import deadlines
from .cases import CaseError, _now, get_case

PARTY_ROLES = ("opponent", "lawyer", "authority", "court", "witness", "me", "other")
DEADLINE_STATUSES = ("open", "done", "missed")
_PARTY_LIMITS = {"name": 200, "address": 500, "contact": 300, "note": 2000}
_P_COLS = ("id", "project_id", "role", "name", "address", "contact", "note", "created_at")
_D_COLS = ("id", "project_id", "label", "event_date", "kind", "amount", "start_rule", "due_date", "calc", "status",
           "note", "created_at")
_N_COLS = ("id", "project_id", "author", "author_name", "title", "body", "citations", "created_at")


def _case(project_id: str) -> dict[str, Any]:
    case = get_case(project_id)
    if case is None:
        raise CaseError("case_not_found", 404)
    return case


def _text(value: Any, field: str, limit: int, *, required: bool = False) -> str:
    val = str(value or "").strip()
    if required and not val:
        raise CaseError("field_required", field=field)
    if len(val) > limit:
        raise CaseError("field_too_long", field=field, max=limit)
    return val


# ── Beteiligte ────────────────────────────────────────────────────────────────

def _party_data(fields: dict[str, Any]) -> dict[str, str]:
    if fields.get("role") not in PARTY_ROLES:
        raise CaseError("role_invalid", allowed=list(PARTY_ROLES))
    data = {"role": fields["role"]}
    for key, limit in _PARTY_LIMITS.items():
        data[key] = _text(fields.get(key), key, limit, required=key == "name")
    return data


def add_party(project_id: str, fields: dict[str, Any]) -> dict[str, Any]:
    _case(project_id)
    data = _party_data(fields)
    with db() as c:
        cur = c.execute("INSERT INTO module_legal_parties(project_id, role, name, address, contact, note, created_at) "
                        "VALUES (?,?,?,?,?,?,?)", (project_id, data["role"], data["name"], data["address"],
                                                   data["contact"], data["note"], _now()))
        row = c.execute(f"SELECT {', '.join(_P_COLS)} FROM module_legal_parties WHERE id = ?",
                        (cur.lastrowid,)).fetchone()
    return dict(zip(_P_COLS, row, strict=True))


def list_parties(project_id: str) -> list[dict[str, Any]]:
    with db() as c:
        rows = c.execute(f"SELECT {', '.join(_P_COLS)} FROM module_legal_parties WHERE project_id = ? ORDER BY id",
                         (project_id,)).fetchall()
    return [dict(zip(_P_COLS, r, strict=True)) for r in rows]


def delete_party(project_id: str, party_id: int) -> None:
    with db() as c:
        if not c.execute("DELETE FROM module_legal_parties WHERE id = ? AND project_id = ?",
                         (party_id, project_id)).rowcount:
            raise CaseError("party_not_found", 404)


# ── Fristen ───────────────────────────────────────────────────────────────────

def calc(fields: dict[str, Any], state: str) -> dict[str, Any]:
    """Frist rechnen ohne zu speichern; Fehler als CaseError."""
    try:
        event = date.fromisoformat(str(fields.get("event_date") or ""))
    except ValueError:
        raise CaseError("event_date_invalid") from None
    try:
        amount = int(fields.get("amount", 0))
    except (TypeError, ValueError):
        raise CaseError("amount_invalid") from None
    try:
        return deadlines.compute(event_date=event, kind=str(fields.get("kind") or ""), amount=amount,
                                 state=state, start=str(fields.get("start_rule") or "event"))
    except ValueError as e:
        raise CaseError("deadline_invalid", detail=str(e)) from None


def _deadline_data(fields: dict[str, Any], state: str) -> dict[str, Any]:
    label = _text(fields.get("label"), "label", 200, required=True)
    result = calc(fields, state)
    return {"label": label, "event_date": result["event_date"], "kind": result["kind"], "amount": result["amount"],
            "start_rule": result["start"], "due_date": result["due_date"],
            "calc": {"steps": result["steps"], "warnings": result["warnings"], "state": state},
            "note": _text(fields.get("note"), "note", 2000)}


def _deadline_row(row: tuple) -> dict[str, Any]:
    d = dict(zip(_D_COLS, row, strict=True))
    d["calc"] = json.loads(d["calc"])
    return d


def _insert_deadline(project_id: str, data: dict[str, Any]) -> dict[str, Any]:
    with db() as c:
        cur = c.execute("INSERT INTO module_legal_deadlines(project_id, label, event_date, kind, amount, start_rule, "
                        "due_date, calc, note, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (project_id, data["label"], data["event_date"], data["kind"], data["amount"],
                         data["start_rule"], data["due_date"], json.dumps(data["calc"], ensure_ascii=False),
                         data["note"], _now()))
        row = c.execute(f"SELECT {', '.join(_D_COLS)} FROM module_legal_deadlines WHERE id = ?",
                        (cur.lastrowid,)).fetchone()
    return _deadline_row(row)


def add_deadline(project_id: str, fields: dict[str, Any]) -> dict[str, Any]:
    case = _case(project_id)
    return _insert_deadline(project_id, _deadline_data(fields, case["state"]))


def list_deadlines(project_id: str) -> list[dict[str, Any]]:
    with db() as c:
        rows = c.execute(f"SELECT {', '.join(_D_COLS)} FROM module_legal_deadlines WHERE project_id = ? "
                         "ORDER BY due_date, id", (project_id,)).fetchall()
    return [_deadline_row(r) for r in rows]


def set_deadline_status(project_id: str, deadline_id: int, status: str) -> None:
    if status not in DEADLINE_STATUSES:
        raise CaseError("status_invalid", allowed=list(DEADLINE_STATUSES))
    with db() as c:
        if not c.execute("UPDATE module_legal_deadlines SET status = ? WHERE id = ? AND project_id = ?",
                         (status, deadline_id, project_id)).rowcount:
            raise CaseError("deadline_not_found", 404)


def delete_deadline(project_id: str, deadline_id: int) -> None:
    with db() as c:
        if not c.execute("DELETE FROM module_legal_deadlines WHERE id = ? AND project_id = ?",
                         (deadline_id, project_id)).rowcount:
            raise CaseError("deadline_not_found", 404)


# ── Notizen ───────────────────────────────────────────────────────────────────

def _check_citations(citations: list[Any]) -> list[dict[str, Any]]:
    from . import norm_view
    out = []
    for raw in citations[:20]:
        text = str(raw or "").strip()[:100]
        if not text:
            continue
        try:
            found = norm_view.lookup(text)
            out.append({"citation": found["citation"], "found": True})
        except norm_view.NormError:
            out.append({"citation": text, "found": False})
    return out


def add_note(project_id: str, *, author: str, author_name: str, title: str, body: str,
             citations: list[Any] | None = None) -> dict[str, Any]:
    _case(project_id)
    if author not in ("agent", "user"):
        raise CaseError("author_invalid")
    data = (_text(title, "title", 200, required=True), _text(body, "body", 20000, required=True))
    checked = _check_citations(list(citations or []))
    with db() as c:
        cur = c.execute("INSERT INTO module_legal_notes(project_id, author, author_name, title, body, citations, "
                        "created_at) VALUES (?,?,?,?,?,?,?)", (project_id, author, author_name[:200], *data,
                                                               json.dumps(checked, ensure_ascii=False), _now()))
        row = c.execute(f"SELECT {', '.join(_N_COLS)} FROM module_legal_notes WHERE id = ?",
                        (cur.lastrowid,)).fetchone()
    return _note_row(row)


def _note_row(row: tuple) -> dict[str, Any]:
    n = dict(zip(_N_COLS, row, strict=True))
    n["citations"] = json.loads(n["citations"])
    return n


def list_notes(project_id: str) -> list[dict[str, Any]]:
    with db() as c:
        rows = c.execute(f"SELECT {', '.join(_N_COLS)} FROM module_legal_notes WHERE project_id = ? ORDER BY id DESC",
                         (project_id,)).fetchall()
    return [_note_row(r) for r in rows]


def delete_note(project_id: str, note_id: int) -> None:
    with db() as c:
        if not c.execute("DELETE FROM module_legal_notes WHERE id = ? AND project_id = ?",
                         (note_id, project_id)).rowcount:
            raise CaseError("note_not_found", 404)


# Vorschläge + Gesamtsicht liegen in proposals.py; hier wieder angeboten, damit Aufrufer nur casefile kennen.
from .proposals import PROPOSAL_KINDS, decide, list_proposals, propose, snapshot  # noqa: F401
