"""Aktionen auf dem Server (PLAN-M2 Schritt 7): gelesen/ungelesen, markieren, verschieben, löschen.

Archiv-Regel (Spec §5): Nur der Server wird geändert. Die Archivdatei bleibt immer; der Index folgt beim Abgleich
(Fundorte), Flags sofort. Sicherheit vor jeder Änderung:
- die UID wird über die Message-ID im Ordner bestätigt (anderes Programm/Umsortierung → überspringen)
- entfernt wird nur gezielt per UID EXPUNGE (UIDPLUS); ohne UIDPLUS bleibt \\Deleted stehen – nie ein pauschales
  EXPUNGE, das von anderen Programmen markierte Mails mitnehmen würde. Auch kein CLOSE (macht dasselbe still).
"""
from __future__ import annotations

import re

from . import imap_conn, index_db

_FLAG = {"seen": ("+", "\\Seen"), "unseen": ("-", "\\Seen"), "flag": ("+", "\\Flagged"), "unflag": ("-", "\\Flagged")}
_COL = {"\\Seen": "seen", "\\Flagged": "flagged"}
ACTIONS = frozenset({*_FLAG, "move", "delete"})
_MSGID_OK = re.compile(r"^<[^<>\s\"\\]{1,500}>$")


class ActionError(ValueError):
    pass


def _caps(conn) -> set[str]:
    typ, data = conn.capability()
    return set((data[0] or b"").decode(errors="replace").upper().split()) if typ == "OK" and data else set()


def _targets(account_id: str, mids: list[int]) -> list[dict]:
    """Je Mail alle Fundorte auf dem Server (Ordner, UID) – nur Mails dieses Kontos."""
    if not mids:
        return []
    q = ",".join("?" * len(mids))
    with index_db.connect() as c:
        rows = c.execute(f"SELECT m.id, m.message_id, f.name AS folder, f.role, l.uid FROM messages m "
                         f"JOIN locations l ON l.message_id=m.id JOIN folders f ON f.id=l.folder_id "
                         f"WHERE m.account_id=? AND m.id IN ({q}) AND l.uid>0 ORDER BY f.name, l.uid",
                         [account_id, *mids]).fetchall()
    return [dict(r) for r in rows]


def _folder_by_role(account_id: str, role: str) -> str | None:
    with index_db.connect() as c:
        r = c.execute("SELECT name FROM folders WHERE account_id=? AND role=? AND gone=0 ORDER BY id LIMIT 1",
                      (account_id, role)).fetchone()
    return r[0] if r else None


def _folder_exists(account_id: str, name: str) -> bool:
    with index_db.connect() as c:
        return c.execute("SELECT 1 FROM folders WHERE account_id=? AND name=? AND gone=0",
                         (account_id, name)).fetchone() is not None


def _confirmed(conn, uid: int, message_id: str) -> bool:
    """Steht unter dieser UID noch genau diese Mail? Ohne gültige Message-ID: lieber nichts anfassen."""
    if not _MSGID_OK.match(message_id or ""):
        return False
    typ, data = conn.uid("SEARCH", f'HEADER Message-ID "{message_id}"')
    if typ != "OK":
        return False
    return str(uid) in (data[0] or b"").decode(errors="replace").split()


def _ok(typ, data, what):
    if typ != "OK":
        raise ActionError(f"{what} abgelehnt: {(data or [b''])[0]!r}"[:200])


def _remove(conn, uid: int, caps: set[str]) -> None:
    _ok(*conn.uid("STORE", str(uid), "+FLAGS.SILENT", "(\\Deleted)"), "Löschen")
    if "UIDPLUS" in caps:
        _ok(*conn.uid("EXPUNGE", str(uid)), "Entfernen")


def _move(conn, uid: int, dest: str, caps: set[str]) -> None:
    if "MOVE" in caps:
        _ok(*conn.uid("MOVE", str(uid), imap_conn.quote(dest)), "Verschieben")
        return
    _ok(*conn.uid("COPY", str(uid), imap_conn.quote(dest)), "Kopieren")
    _remove(conn, uid, caps)


def _leave(conn, caps: set[str]) -> None:
    """Ordner verlassen OHNE CLOSE: CLOSE entfernt still alle \\Deleted-Mails (RFC 3501 6.4.2) – auch fremde.
    UNSELECT (RFC 3691) oder ein SELECT nur zum Lesen beendet den Schreibzugriff ohne zu löschen."""
    try:
        if "UNSELECT" in caps:
            conn.unselect()
        else:
            conn.select("INBOX", readonly=True)
    except Exception:  # noqa: BLE001 - Verlassen darf nichts mehr kaputtmachen
        pass


def _set_flag_index(mid: int, flag: str, on: bool) -> None:
    with index_db.connect() as c:
        c.execute(f"UPDATE messages SET {_COL[flag]}=? WHERE id=?", (int(on), mid))


def _one(acc: dict, conn, action: str, t: dict, caps: set[str], target: str | None) -> None:
    if action in _FLAG:
        op, flag = _FLAG[action]
        _ok(*conn.uid("STORE", str(t["uid"]), f"{op}FLAGS.SILENT", f"({flag})"), "Markieren")
        _set_flag_index(t["id"], flag, op == "+")
    elif action == "move":
        if t["folder"] != target:
            _move(conn, t["uid"], target, caps)
    else:                                   # delete: in den Papierkorb; im Papierkorb (oder ohne) endgültig
        trash = _folder_by_role(acc["id"], "trash")
        if trash and t["folder"] != trash:
            _move(conn, t["uid"], trash, caps)
        else:
            _remove(conn, t["uid"], caps)


def apply(acc: dict, conn, action: str, mids: list[int], *, target: str | None = None) -> dict:
    """conn: angemeldete IMAP-Verbindung. Gibt {"done", "skipped"} zurück (je Mail, nicht je Fundort)."""
    if action not in ACTIONS:
        raise ActionError("unbekannte Aktion")
    if action == "move" and not (target and _folder_exists(acc["id"], target)):
        raise ActionError("Zielordner unbekannt")
    caps = _caps(conn)
    by_folder: dict[str, list[dict]] = {}
    taken: set[int] = set()
    for t in _targets(acc["id"], [int(m) for m in mids]):
        if action in ("move", "delete") and t["id"] in taken:
            continue                        # eine Mail nur einmal verschieben/löschen (Gmail: mehrere Labels)
        taken.add(t["id"])
        by_folder.setdefault(t["folder"], []).append(t)
    done = set()
    for folder, items in by_folder.items():
        typ, _ = conn.select(imap_conn.quote(folder), readonly=False)
        if typ != "OK":
            continue
        for t in items:
            if _confirmed(conn, t["uid"], t["message_id"]):
                _one(acc, conn, action, t, caps, target)
                done.add(t["id"])
        _leave(conn, caps)
    wanted = {int(m) for m in mids}
    return {"done": len(done & wanted), "skipped": len(wanted - done)}
