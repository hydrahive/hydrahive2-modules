"""Abgleich eines Kontos (PLAN-M1 Schritt 7): alle Ordner, alle Jahre, in Paketen; nur Neues; nie löschen.

Je Ordner: UIDVALIDITY prüfen, Flags aller UIDs holen, unbekannte UIDs paketweise laden (BODY.PEEK[] – setzt kein
Gelesen), Fundorte, die es nicht mehr gibt, vergessen. Am Ende: Mails ohne Fundort → deleted_on_server, verschobene
Mails → Archivdatei umziehen. Bricht die Verbindung ab, ist alles bis zum letzten Paket gesichert.
"""
from __future__ import annotations

import imaplib
import re

from . import archive, imap_conn, parse, sent_link, store

BATCH = 200
_FETCH = re.compile(rb"UID (\d+)")
_FLAGS = re.compile(rb"FLAGS \(([^)]*)\)")
_SIZE = re.compile(rb"RFC822\.SIZE (\d+)")
_MSGID = re.compile(rb"(?im)^message-id:\s*(<[^<>\s]{1,500}>)")


class SyncError(RuntimeError):
    pass


class AuthFailed(SyncError):
    pass


def _ok(typ, data, what):
    if typ != "OK":
        raise SyncError(f"{what}: {data[:1]!r}"[:200])
    return data


def _meta(line: bytes) -> tuple[int, set[str], int]:
    uid = int(_FETCH.search(line).group(1))
    fl = _FLAGS.search(line)
    size = _SIZE.search(line)
    return uid, set((fl.group(1).decode(errors="replace").split()) if fl else ()), int(size.group(1)) if size else -1


def _bodies(conn, uids: list[int]) -> list[tuple[int, set[str], bytes]]:
    data = _ok(*conn.uid("FETCH", ",".join(map(str, uids)), "(UID FLAGS BODY.PEEK[])"), "FETCH")
    out = []
    for item in data:
        if isinstance(item, tuple) and len(item) == 2 and b"UID" in item[0]:
            uid, flags, _ = _meta(item[0])
            out.append((uid, flags, item[1]))
    return out


def _uidvalidity(conn) -> int:
    _, data = conn.response("UIDVALIDITY")
    try:
        return int((data or [b"0"])[-1] or 0)
    except (TypeError, ValueError):
        return 0


def _flags_all(conn) -> dict[int, tuple[set[str], int, str]]:
    data = _ok(*conn.uid("FETCH", "1:*", "(UID FLAGS RFC822.SIZE BODY.PEEK[HEADER.FIELDS (MESSAGE-ID)])"), "FETCH")
    out = {}
    for item in data:
        head = item[0] if isinstance(item, tuple) else item
        if not isinstance(head, bytes) or b"UID" not in head:
            continue
        uid, flags, size = _meta(head)
        mid = _MSGID.search(item[1]) if isinstance(item, tuple) else None
        out[uid] = (flags, size, mid.group(1).decode(errors="replace") if mid else "")
    return out


def _folder(acc: dict, conn, info: dict, batch: int, counts: dict, on_progress=None) -> set[int]:
    fid = store.folder(acc["id"], info["name"], role=info["role"])
    typ, _ = conn.select(imap_conn.quote(info["name"]), readonly=True)
    if typ != "OK":
        return set()
    store.check_uidvalidity(fid, _uidvalidity(conn))   # Wechsel → alte UIDs gelten nicht mehr (RFC 3501 2.3.1.1)
    server = _flags_all(conn)
    known = store.known_uids(fid)
    store.set_flags(fid, {u: f for u, (f, _, _) in server.items() if u in known})
    todo = []
    for uid, (flags, size, mid) in sorted(server.items()):
        if uid in known:
            continue
        hit = store.find_header(acc["id"], mid, size) if size >= 0 else None
        if hit:
            store.add_location(hit["id"], fid, uid, flags)
        else:
            todo.append(uid)
    for i in range(0, len(todo), batch):
        for uid, flags, raw in _bodies(conn, todo[i:i + batch]):
            p = parse.parse(raw)
            existed = store.find_header(acc["id"], p.message_id, len(raw)) if p.message_id else None
            rel = existed["path"] if existed else archive.store(acc["address"], info["name"], raw, date=p.date,
                                                                 subject=p.subject)
            store.add_message(acc["id"], fid, uid, p, path=rel, size=len(raw), flags=flags)
            if not existed:
                archive.manifest_add(acc["address"], rel, p.message_id, info["name"], "ok")
                counts["new"] += 1
        store.recount(fid)                  # Zähler nach jedem Paket – sonst sieht man stundenlang „0“
        if on_progress:
            on_progress(dict(counts))
    store.drop_locations(fid, keep_uids=set(server))
    store.recount(fid)
    return {fid}


def _folder_names(conn) -> list[dict]:
    return imap_conn.parse_list(_ok(*conn.list('""', "*"), "LIST"))


def sync_account(acc: dict, conn, *, login: tuple[str, str] | None = None, batch: int = BATCH,
                 on_progress=None) -> dict:
    """on_progress(counts) nach jedem Paket und jedem Ordner (Fortschritt in der Oberfläche)."""
    counts = {"new": 0, "gone": 0, "folders": 0, "folders_total": 0}
    try:
        if login:
            try:
                conn.login(*login)
            except imaplib.IMAP4.error as e:
                raise AuthFailed(str(e)[:200]) from None
        seen = set()
        infos = sorted(_folder_names(conn), key=lambda f: f["role"] != "inbox")   # Posteingang zuerst
        for info in infos:                  # alle Ordner sofort sichtbar, auch wenn ihr Inhalt noch kommt
            store.folder(acc["id"], info["name"], role=info["role"])
        counts["folders_total"] = len(infos)
        if on_progress:
            on_progress(dict(counts))
        for info in infos:
            seen |= _folder(acc, conn, info, batch, counts, on_progress)
            counts["folders"] += 1
            if on_progress:
                on_progress(dict(counts))
        _mark_missing_folders(acc["id"], seen)
        r = store.reconcile(acc["id"])
        sent_link.adopt_legacy(acc["id"])           # Bestand aus 0.2.0
        sent_link.refresh(acc["id"])                # eigene Gesendet-Kopie ↔ (umgeschriebene) Server-Fassung
        counts["gone"] = r["gone"]
        _apply_moves(acc, r["moves"])
    except (imaplib.IMAP4.abort, OSError) as e:
        raise SyncError(f"Verbindung abgebrochen: {e}"[:200]) from None
    return counts


def _mark_missing_folders(account_id: str, seen: set[int]) -> None:
    from . import index_db
    with index_db.connect() as c:
        ids = [r[0] for r in c.execute("SELECT id FROM folders WHERE account_id=? AND gone=0", (account_id,))]
        for fid in set(ids) - seen:
            c.execute("UPDATE folders SET gone=1 WHERE id=?", (fid,))
            c.execute("DELETE FROM locations WHERE folder_id=?", (fid,))


def _apply_moves(acc: dict, moves: list) -> None:
    from . import index_db
    for mid, rel, fid in moves:
        with index_db.connect() as c:
            name = c.execute("SELECT name FROM folders WHERE id=?", (fid,)).fetchone()[0]
        try:
            new = archive.move(rel, acc["address"], name)
        except archive.ArchiveError:
            continue  # Datei bleibt, wo sie ist; Index zeigt weiter darauf
        store.set_primary(mid, fid, new)
