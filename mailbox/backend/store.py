"""Index-Zugriffe (PLAN-M1 Schritt 6): Ordner, Nachrichten (eindeutig je Konto über den Hash), Flags, Server-Löschung.

Eine Mail, die auf dem Server verschwindet, bleibt im Index (`deleted_on_server`, UID leer) – wie im Archiv.
Ohne FTS5 wird nur der Volltext übersprungen; Suche fällt dann auf Kopfdaten + Kurztext zurück (search.py).
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


def add_message(account_id: str, folder_id: int, uid: int | None, p: Parsed, *, path: str, size: int,
                flags: set[str]) -> int:
    seen, flagged, answered = _flags(flags)
    with index_db.connect() as c:
        old = c.execute("SELECT id FROM messages WHERE account_id=? AND sha256=?", (account_id, p.sha256)).fetchone()
        if old:
            c.execute("UPDATE messages SET folder_id=?, uid=?, path=?, seen=?, flagged=?, answered=?, "
                      "deleted_on_server=0 WHERE id=?", (folder_id, uid, path, seen, flagged, answered, old[0]))
            return old[0]
        cur = c.execute(
            "INSERT INTO messages(account_id, folder_id, uid, message_id, sha256, thread_key, in_reply_to, date, "
            "from_addr, to_addr, cc_addr, subject, snippet, seen, flagged, answered, size, attachments, path, parse_error) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (account_id, folder_id, uid, p.message_id, p.sha256, p.thread_key, p.in_reply_to, p.date, p.from_addr,
             p.to_addr, p.cc_addr, p.subject, p.snippet, seen, flagged, answered, size,
             json.dumps(p.attachments, ensure_ascii=False), path, p.error))
        _fts(c, cur.lastrowid, p)
        return cur.lastrowid


def known_uids(folder_id: int) -> set[int]:
    with index_db.connect() as c:
        return {r[0] for r in c.execute("SELECT uid FROM messages WHERE folder_id=? AND uid IS NOT NULL", (folder_id,))}


def set_flags(folder_id: int, by_uid: dict[int, set[str]]) -> None:
    with index_db.connect() as c:
        c.executemany("UPDATE messages SET seen=?, flagged=?, answered=? WHERE folder_id=? AND uid=?",
                      [(*_flags(f), folder_id, uid) for uid, f in by_uid.items()])


def mark_gone(folder_id: int, *, keep_uids: set[int]) -> int:
    """Auf dem Server nicht mehr vorhandene UIDs: als gelöscht markieren (bleiben im Archiv). Rückgabe: Anzahl."""
    gone = known_uids(folder_id) - set(keep_uids)
    with index_db.connect() as c:
        c.executemany("UPDATE messages SET deleted_on_server=1, uid=NULL WHERE folder_id=? AND uid=?",
                      [(folder_id, u) for u in gone])
    return len(gone)


def recount(folder_id: int) -> None:
    with index_db.connect() as c:
        c.execute("UPDATE folders SET total=(SELECT count(*) FROM messages WHERE folder_id=? AND deleted_on_server=0), "
                  "unread=(SELECT count(*) FROM messages WHERE folder_id=? AND deleted_on_server=0 AND seen=0) "
                  "WHERE id=?", (folder_id, folder_id, folder_id))
