"""Anrufe annehmen: Schalter, Ansage, Testfenster, Anrufliste (PLAN-ANRUFE-2A Schritt 7).

``policy(cid)`` und ``record(cid, …)`` werden vom laufenden SipAgent aus seinem Thread aufgerufen; sie lesen den
aktuellen Stand aus der DB, deshalb muss beim Ändern von Schalter/Ansage nicht neu angemeldet werden.
Ein Testfenster (60 s) nimmt genau einen Anruf an, auch wenn der Schalter aus ist.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone

from hydrahive.db._utils import now_iso
from hydrahive.db.connection import db

TEST_SECONDS = 60
# Nicht angenommen bzw. nie verbunden → keine Anrufart
_NOT_TAKEN = {"rejected", "busy", "codec", "no_port", "cancelled", "no_answer", "declined", "invalid_number",
              "failed", "auth_failed", "unreachable"}
KEEP = 50
DEFAULT_GREETING = ("Hallo, hier ist der Telefonassistent von HydraHive. Im Moment ist leider niemand erreichbar. "
                    "Bitte versuchen Sie es später noch einmal. Auf Wiederhören.")


class NotFound(LookupError):
    pass


class Conflict(ValueError):
    pass


class NoCallbackNumber(LookupError):
    pass


def _now() -> float:
    return time.time()


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).isoformat(timespec="seconds")


def _ts(iso: str | None) -> float:
    return datetime.fromisoformat(iso).timestamp() if iso else 0.0


def _notes(raw) -> dict:
    """Nur bekannte Notizfelder, begrenzt (gleiche Regeln wie bei der Modellantwort)."""
    from .agent.reply import _notes as clean
    return clean(raw)


def greeting_text(row) -> str:
    return (row["greeting"] or "").strip() or DEFAULT_GREETING


def open_window(row) -> str | None:
    """Testfenster-Ende, solange es offen ist (sonst None)."""
    return row["test_until"] if _ts(row["test_until"]) > _now() else None


def policy(cid: str) -> str | None:
    with db() as c:
        row = c.execute("SELECT answer_calls, greeting, test_until FROM module_telephony_connections WHERE id=?",
                        (cid,)).fetchone()
    if not row:
        return None
    if row["answer_calls"] or _ts(row["test_until"]) > _now():
        return greeting_text(row)
    return None


def record(cid: str, info: dict) -> None:
    with db() as c:
        row = c.execute("SELECT test_until FROM module_telephony_connections WHERE id=?", (cid,)).fetchone()
        if not row:
            return
        is_test = _ts(row["test_until"]) > _now() and info.get("result") != "busy"
        notes = _notes(info.get("notes"))
        direction = "out" if info.get("direction") == "out" else "in"
        is_test = is_test and direction == "in"
        result = str(info.get("result", ""))
        kind = "" if result in _NOT_TAKEN else ("assistant" if info.get("kind") == "assistant" else "greeting")
        c.execute("INSERT INTO module_telephony_calls(connection_id, started_at, number, result, codec, rtp_out, "
                  "rtp_in, is_test, turns, notes, notes_read, direction, kind) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  (cid, now_iso(), str(info.get("number", "unbekannt"))[:20], str(info.get("result", ""))[:20],
                   str(info.get("codec", ""))[:8], int(info.get("rtp_out", 0)), int(info.get("rtp_in", 0)),
                   int(is_test), int(info.get("turns", 0)), json.dumps(notes, ensure_ascii=False) if notes else "",
                   0 if notes else 1, direction, kind))
        if is_test:
            c.execute("UPDATE module_telephony_connections SET test_until=NULL WHERE id=?", (cid,))
        c.execute("DELETE FROM module_telephony_calls WHERE connection_id=? AND id NOT IN (SELECT id FROM "
                  "module_telephony_calls WHERE connection_id=? ORDER BY id DESC LIMIT ?)", (cid, cid, KEEP))


def _cid(user_id: str) -> str:
    with db() as c:
        row = c.execute("SELECT id FROM module_telephony_connections WHERE owner=?", (f"user:{user_id}",)).fetchone()
    if not row:
        raise NotFound(user_id)
    return row["id"]


def update(user_id: str, answer_calls: bool, greeting: str, assistant: dict | None = None) -> None:
    """assistant: {mode, assistant_name, assistant_knowledge, assistant_model} oder None (= unverändert lassen)."""
    cid = _cid(user_id)
    with db() as c:
        c.execute("UPDATE module_telephony_connections SET answer_calls=?, greeting=?, updated_at=? WHERE id=?",
                  (int(answer_calls), greeting, now_iso(), cid))
        if assistant is not None:
            c.execute("UPDATE module_telephony_connections SET call_mode=?, assistant_name=?, assistant_knowledge=?, "
                      "assistant_model=? WHERE id=?", (assistant["mode"], assistant["assistant_name"],
                                                        assistant["assistant_knowledge"],
                                                        assistant["assistant_model"], cid))


def open_test(user_id: str) -> str:
    cid, until = _cid(user_id), _iso(_now() + TEST_SECONDS)
    with db() as c:
        c.execute("UPDATE module_telephony_connections SET test_until=? WHERE id=?", (until, cid))
    return until


def _public(r) -> dict:
    return {"id": r["id"], "started_at": r["started_at"], "number": r["number"], "result": r["result"],
            "codec": r["codec"], "rtp_out": r["rtp_out"], "rtp_in": r["rtp_in"], "is_test": bool(r["is_test"]),
            "heard": None if r["heard"] is None else bool(r["heard"]), "turns": r["turns"],
            "notes": json.loads(r["notes"]) if r["notes"] else {}, "notes_read": bool(r["notes_read"]),
            "direction": r["direction"], "kind": r["kind"]}


def list_for(user_id: str) -> list[dict]:
    cid = _cid(user_id)
    with db() as c:
        rows = c.execute("SELECT * FROM module_telephony_calls WHERE connection_id=? ORDER BY id DESC LIMIT ?",
                         (cid, KEEP)).fetchall()
    return [_public(r) for r in rows]


def unread(user_id: str) -> int:
    cid = _cid(user_id)
    with db() as c:
        return c.execute("SELECT COUNT(*) FROM module_telephony_calls WHERE connection_id=? AND notes_read=0",
                         (cid,)).fetchone()[0]


def mark_read(user_id: str, call_id: int) -> dict:
    cid = _cid(user_id)
    with db() as c:
        r = c.execute("SELECT id FROM module_telephony_calls WHERE id=? AND connection_id=?", (call_id, cid)).fetchone()
        if not r:
            raise NotFound(str(call_id))
        c.execute("UPDATE module_telephony_calls SET notes_read=1 WHERE id=?", (call_id,))
        return _public(c.execute("SELECT * FROM module_telephony_calls WHERE id=?", (call_id,)).fetchone())


def confirm(user_id: str, call_id: int, heard: bool) -> dict:
    cid = _cid(user_id)
    with db() as c:
        r = c.execute("SELECT * FROM module_telephony_calls WHERE id=? AND connection_id=?", (call_id, cid)).fetchone()
        if not r:
            raise NotFound(str(call_id))
        if not r["is_test"]:
            raise Conflict("nur Testanrufe")
        c.execute("UPDATE module_telephony_calls SET heard=? WHERE id=?", (int(heard), call_id))
        r = c.execute("SELECT * FROM module_telephony_calls WHERE id=?", (call_id,)).fetchone()
    return _public(r)


def callback(user_id: str, call_id: int) -> dict:
    """Vorschlag für „Zurückrufen“ (PLAN-ANRUFEN-3, 3b): Nummer aus der Notiz + Auftrag. Gewählt wird erst per Knopf."""
    cid = _cid(user_id)
    with db() as c:
        r = c.execute("SELECT notes FROM module_telephony_calls WHERE id=? AND connection_id=?", (call_id, cid)).fetchone()
    if not r:
        raise NotFound(str(call_id))
    notes = json.loads(r["notes"]) if r["notes"] else {}
    number = (notes.get("callback_number") or "").strip()
    if not number:
        raise NoCallbackNumber(str(call_id))
    who = notes.get("name") or "der Anrufer"
    about = notes.get("concern") or notes.get("summary") or "die hinterlassene Nachricht"
    task = (f"Rückruf an {who}. Anliegen laut Notiz: {about}. Sag, dass die Nachricht angekommen ist, "
            "frag nach, worum es genau geht und wann ein Gespräch passt. Nichts zusagen.")
    return {"number": number, "task": task[:1000]}


def greeting_of(cid: str) -> str:
    """Ansagetext der Verbindung (für „Mit Ansage annehmen“ ohne eigenen Text)."""
    with db() as c:
        row = c.execute("SELECT greeting FROM module_telephony_connections WHERE id=?", (cid,)).fetchone()
    return greeting_text(row) if row else DEFAULT_GREETING
