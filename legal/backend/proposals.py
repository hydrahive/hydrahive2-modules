"""Vorschläge des Rechts-Agenten (Plan L2 Schritt 5): ändern die Fallakte erst bei ``decide(accept=True)``.

Eine Frist wird schon beim Vorschlag gerechnet (mit dem Land des Falls), damit der Mensch Ergebnis und Rechenweg sieht,
bevor er übernimmt. ``decide`` markiert zuerst (Doppelklick legt nichts doppelt an) und setzt bei Fehlern zurück.
"""
from __future__ import annotations

import json
from typing import Any

from hydrahive.db.connection import db

from . import casefile as cf
from .cases import CaseError, _now, get_case
from .holidays_de import STATES

PROPOSAL_KINDS = ("party", "deadline", "fact", "letter")
_PR_COLS = ("id", "project_id", "kind", "payload", "author_name", "status", "created_at", "decided_by", "decided_at")


def _proposal_payload(kind: str, payload: dict[str, Any], state: str, case: dict[str, Any]) -> dict[str, Any]:
    if kind == "party":
        return cf._party_data(payload)
    if kind == "deadline":
        return cf._deadline_data(payload, state)
    if kind == "fact":
        return {"text": cf._text(payload.get("text"), "text", 5000, required=True)}
    if kind == "letter":
        return _letter_payload(payload, case)
    raise CaseError("proposal_kind_invalid", allowed=list(PROPOSAL_KINDS))


def _letter_payload(payload: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    """Brief-Vorschlag: gleiche Prüfung wie der Schriftverkehr, dazu die Prüfliste zum Zeitpunkt des Vorschlags."""
    from . import correspondence, letter_check
    if not str(payload.get("body") or "").strip():
        raise CaseError("field_required", field="body")
    data = correspondence._clean(payload, partial=False)
    data["attachments"] = json.loads(data["attachments"])
    data["check"] = letter_check.check(data, case=case)
    return data


def _proposal_row(row: tuple) -> dict[str, Any]:
    p = dict(zip(_PR_COLS, row, strict=True))
    p["payload"] = json.loads(p["payload"])
    return p


def propose(project_id: str, kind: str, payload: dict[str, Any], *, author_name: str) -> dict[str, Any]:
    case = cf._case(project_id)
    data = _proposal_payload(kind, payload if isinstance(payload, dict) else {}, case["state"], case)
    with db() as c:
        cur = c.execute("INSERT INTO module_legal_proposals(project_id, kind, payload, author_name, created_at) "
                        "VALUES (?,?,?,?,?)", (project_id, kind, json.dumps(data, ensure_ascii=False),
                                               author_name[:200], _now()))
        row = c.execute(f"SELECT {', '.join(_PR_COLS)} FROM module_legal_proposals WHERE id = ?",
                        (cur.lastrowid,)).fetchone()
    return _proposal_row(row)


def list_proposals(project_id: str, *, only_open: bool = True) -> list[dict[str, Any]]:
    where = " AND status = 'open'" if only_open else ""
    with db() as c:
        rows = c.execute(f"SELECT {', '.join(_PR_COLS)} FROM module_legal_proposals WHERE project_id = ?{where} "
                         "ORDER BY id", (project_id,)).fetchall()
    return [_proposal_row(r) for r in rows]


def _apply(project_id: str, kind: str, payload: dict[str, Any], by: str) -> None:
    if kind == "party":
        cf.add_party(project_id, payload)
    elif kind == "deadline":
        cf._insert_deadline(project_id, payload)
    elif kind == "letter":
        from . import correspondence
        fields = {k: v for k, v in payload.items() if k != "check"}
        correspondence.add(project_id, {**fields, "direction": "out"}, by=by)
    else:
        facts = (get_case(project_id) or {}).get("facts", "")
        new = f"{facts.rstrip()}\n\n{payload['text']}" if facts.strip() else payload["text"]
        with db() as c:
            c.execute("UPDATE module_legal_cases SET facts = ?, updated_at = ? WHERE project_id = ?",
                      (new[:20000], _now(), project_id))


def decide(project_id: str, proposal_id: int, *, accept: bool, by: str) -> dict[str, Any]:
    cf._case(project_id)
    with db() as c:
        row = c.execute(f"SELECT {', '.join(_PR_COLS)} FROM module_legal_proposals WHERE id = ? AND project_id = ?",
                        (proposal_id, project_id)).fetchone()
        if row is None:
            raise CaseError("proposal_not_found", 404)
        if row[_PR_COLS.index("status")] != "open":
            raise CaseError("proposal_decided", 409)
        # Erst als entschieden markieren (Doppelklick legt nichts doppelt an), dann anwenden.
        n = c.execute("UPDATE module_legal_proposals SET status = ?, decided_by = ?, decided_at = ? "
                      "WHERE id = ? AND status = 'open'",
                      ("accepted" if accept else "rejected", by, _now(), proposal_id)).rowcount
    if not n:
        raise CaseError("proposal_decided", 409)
    proposal = _proposal_row(row)
    if accept:
        try:
            _apply(project_id, proposal["kind"], proposal["payload"], by)
        except Exception:
            with db() as c:
                c.execute("UPDATE module_legal_proposals SET status = 'open', decided_by = NULL, decided_at = NULL "
                          "WHERE id = ?", (proposal_id,))
            raise
    return {**proposal, "status": "accepted" if accept else "rejected"}


def snapshot(project_id: str) -> dict[str, Any]:
    """Gesamtsicht der Fallakte (Werkzeug legal_case, Fallakte-Seite)."""
    case = cf._case(project_id)
    return {"case": case, "state_name": STATES[case["state"]], "parties": cf.list_parties(project_id),
            "deadlines": cf.list_deadlines(project_id), "notes": cf.list_notes(project_id),
            "correspondence": _correspondence(project_id), "open_proposals": len(list_proposals(project_id))}


def _correspondence(project_id: str) -> list[dict[str, Any]]:
    from . import correspondence
    return correspondence.list_for(project_id)
