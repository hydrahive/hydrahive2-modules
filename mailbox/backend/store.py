"""Index-Zugriffe (PLAN-M1 Schritt 6): Ordner, Nachrichten (eindeutig je Konto über den Hash), Fundorte, Flags.

Eine Mail kann auf dem Server in mehreren Ordnern liegen (Gmail-Labels) → `locations`. Der Hauptordner
(`messages.folder_id`, bestimmt den Archivpfad) wechselt nur, wenn die Mail aus ihm verschwindet und anderswo liegt.
Liegt sie nirgends mehr, bleibt sie im Index und Archiv (`deleted_on_server`) – gelöscht wird nie.
"""
from __future__ import annotations

import json

from . import index_db
from .parse import Parsed

_FLAG_COLS = {"\\Seen": "seen", "\\Flagged": "flagged", "\\Answered": "answered"}


def folder(account_id: str, name: str, *, role: str = "") -> int:
    with index_db.connect() as c:
        c.execute("INSERT INTO folders(account_id, name, role) VALUES (?,?,?) "
                  "ON CONFLICT(account_id, name) DO UPDATE SET role=excluded.role, gone=0", (account_id, name, role))
        return c.execute("SELECT id FROM folders WHERE account_id=? AND name=?", (account_id, name)).fetchone()[0]


def _flags(flags: set[str]) -> tuple[int, int, int]:
    return tuple(int(f in flags) for f in _FLAG_COLS)  # type: ignore[return-value]


def _fts(c, rowid: int, p: Parsed) -> None:
    if c.execute("SELECT 1 FROM sqlite_master WHERE name='messages_fts'").fetchone():
        c.execute("INSERT INTO messages_fts(rowid, subject, from_addr, to_addr, body) VALUES (?,?,?,?,?)",
                  (rowid, p.subject, p.from_addr, f"{p.to_addr} {p.cc_addr}", p.body))


def _locate(c, mid: int, folder_id: int, uid: int, flags: set[str]) -> None:
    c.execute("INSERT INTO locations(message_id, folder_id, uid) VALUES (?,?,?) "
              "ON CONFLICT(folder_id, uid) DO UPDATE SET message_id=excluded.message_id", (mid, folder_id, uid))
    c.execute("UPDATE messages SET seen=?, flagged=?, answered=?, deleted_on_server=0 WHERE id=?", (*_flags(flags), mid))


def add_message(account_id: str, folder_id: int, uid: int, p: Parsed, *, path: str, size: int, flags: set[str]) -> int:
    with index_db.connect() as c:
        old = c.execute("SELECT id FROM messages WHERE account_id=? AND sha256=?", (account_id, p.sha256)).fetchone()
        if old:
            _locate(c, old[0], folder_id, uid, flags)
            return old[0]
        cur = c.execute(
            "INSERT INTO messages(account_id, folder_id, message_id, sha256, thread_key, in_reply_to, date, from_addr, "
            "to_addr, cc_addr, subject, snippet, size, attachments, path, parse_error) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (account_id, folder_id, p.message_id, p.sha256, p.thread_key, p.in_reply_to, p.date, p.from_addr,
             p.to_addr, p.cc_addr, p.subject, p.snippet, size, json.dumps(p.attachments, ensure_ascii=False), path,
             p.error))
        _fts(c, cur.lastrowid, p)
        _locate(c, cur.lastrowid, folder_id, uid, flags)
        return cur.lastrowid


def find_header(account_id: str, message_id: str, size: int) -> dict | None:
    """Bekannte Mail ohne Inhalt laden erkennen (neue UID nach UIDVALIDITY-Wechsel/Verschieben): Message-ID + Größe."""
    if not message_id:
        return None
    with index_db.connect() as c:
        r = c.execute("SELECT id, path, folder_id FROM messages WHERE account_id=? AND message_id=? AND size=?",
                      (account_id, message_id, size)).fetchone()
    return dict(r) if r else None


def add_location(mid: int, folder_id: int, uid: int, flags: set[str]) -> None:
    with index_db.connect() as c:
        _locate(c, mid, folder_id, uid, flags)


def check_uidvalidity(folder_id: int, value: int) -> bool:
    """Neue UIDVALIDITY: alle Fundorte des Ordners vergessen (die Mails bleiben; der Abgleich findet sie über
    Message-ID + Größe wieder oder lädt sie neu). Unbekannter Wert (0) ändert nichts. True = gewechselt."""
    if not value:
        return False
    with index_db.connect() as c:
        old = c.execute("SELECT uidvalidity FROM folders WHERE id=?", (folder_id,)).fetchone()[0]
        if old == value:
            return False
        if old:
            c.execute("DELETE FROM locations WHERE folder_id=?", (folder_id,))
        c.execute("UPDATE folders SET uidvalidity=?, last_uid=0 WHERE id=?", (value, folder_id))
        return bool(old)


def known_uids(folder_id: int) -> set[int]:
    with index_db.connect() as c:
        return {r[0] for r in c.execute("SELECT uid FROM locations WHERE folder_id=?", (folder_id,))}


def set_flags(folder_id: int, by_uid: dict[int, set[str]]) -> None:
    with index_db.connect() as c:
        c.executemany("UPDATE messages SET seen=?, flagged=?, answered=? WHERE id=(SELECT message_id FROM locations "
                      "WHERE folder_id=? AND uid=?)", [(*_flags(f), folder_id, uid) for uid, f in by_uid.items()])


def drop_locations(folder_id: int, *, keep_uids: set[int]) -> int:
    """Fundorte, die es auf dem Server nicht mehr gibt, vergessen (die Mail selbst bleibt). Rückgabe: Anzahl."""
    gone = known_uids(folder_id) - set(keep_uids)
    with index_db.connect() as c:
        c.executemany("DELETE FROM locations WHERE folder_id=? AND uid=?", [(folder_id, u) for u in gone])
    return len(gone)


def reconcile(account_id: str) -> dict:
    """Nach dem Ordnerdurchlauf: Mails ohne Fundort → deleted_on_server; Hauptordner weg, aber anderswo da → Umzug."""
    with index_db.connect() as c:
        cur = c.execute("UPDATE messages SET deleted_on_server=1 WHERE account_id=? AND deleted_on_server=0 AND "
                        "NOT EXISTS (SELECT 1 FROM locations l WHERE l.message_id=messages.id)", (account_id,))
        moves = [(r[0], r[1], r[2]) for r in c.execute(
            "SELECT m.id, m.path, min(l.folder_id) FROM messages m JOIN locations l ON l.message_id=m.id "
            "WHERE m.account_id=? AND NOT EXISTS (SELECT 1 FROM locations x WHERE x.message_id=m.id "
            "AND x.folder_id=m.folder_id) GROUP BY m.id", (account_id,))]
    return {"gone": cur.rowcount, "moves": moves}


def set_primary(mid: int, folder_id: int, path: str) -> None:
    with index_db.connect() as c:
        c.execute("UPDATE messages SET folder_id=?, path=? WHERE id=?", (folder_id, path, mid))


def recount(folder_id: int) -> None:
    with index_db.connect() as c:
        c.execute("UPDATE folders SET total=(SELECT count(*) FROM locations WHERE folder_id=?), "
                  "unread=(SELECT count(*) FROM locations l JOIN messages m ON m.id=l.message_id "
                  "WHERE l.folder_id=? AND m.seen=0) WHERE id=?", (folder_id, folder_id, folder_id))
