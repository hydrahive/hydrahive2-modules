"""Senden als Ablauf (PLAN-M2 Schritt 5): Grenze → SMTP → Zählung → Archivkopie → Ablage im Gesendet-Ordner.

Grundsatz (regel.nichts-kaputt-lassen): Ist die Mail per SMTP raus, ist das Ergebnis „gesendet“ – alles danach
(Zählung, Archiv, Server-Ablage) darf nur noch Warnungen erzeugen, nie einen Fehler. Sonst sendet der Nutzer doppelt.

Die Archivkopie entsteht immer (das Archiv ist das Backup) und mit genau den gesendeten Bytes. Legt der Server
die Kopie ab, findet der nächste Abgleich dieselbe Mail (gleicher Hash) und vermerkt nur den Fundort.
Gmail legt gesendete Mails selbst ab → kein APPEND (sonst doppelt im Gesendet-Ordner).
"""
from __future__ import annotations

import logging
import re

from . import archive, imap_conn, index_db, parse, ratelimit, sent_link, smtp_send, store

log = logging.getLogger("hydrahive.modules.mailbox")
SELF_FILING = ("imap.gmail.com",)


def _sent_folder(account_id: str) -> str | None:
    with index_db.connect() as c:
        r = c.execute("SELECT name FROM folders WHERE account_id=? AND role='sent' AND gone=0 ORDER BY id LIMIT 1",
                      (account_id,)).fetchone()
    return r[0] if r else None


def _archive_copy(acc: dict, raw: bytes, folder: str) -> int:
    """Archiv + Index; uid=0 heißt „noch kein Fundort auf dem Server“ (wird beim Abgleich ersetzt)."""
    p = parse.parse(raw)
    rel = archive.store(acc["address"], folder, raw, date=p.date, subject=p.subject)
    fid = store.folder(acc["id"], folder, role="sent" if folder != "Gesendet (lokal)" else "")
    mid = store.add_message(acc["id"], fid, 0, p, path=rel, size=len(raw), flags={"\\Seen"})
    with index_db.connect() as c:
        c.execute("DELETE FROM locations WHERE message_id=? AND uid=0", (mid,))
        c.execute("UPDATE messages SET deleted_on_server=1 WHERE id=? AND NOT EXISTS "
                  "(SELECT 1 FROM locations l WHERE l.message_id=?)", (mid, mid))
    archive.manifest_add(acc["address"], rel, p.message_id, folder, "sent")
    sent_link.mark(mid)
    return mid


_APPENDUID = re.compile(rb"\[APPENDUID (\d+) (\d+)\]", re.IGNORECASE)


def _append(acc: dict, password: str, folder: str, raw: bytes, open_imap) -> tuple[int, int] | None:
    """Ablegen; Rückgabe (UIDVALIDITY, UID) aus der APPENDUID-Antwort (UIDPLUS, RFC 4315), sonst None."""
    conn = open_imap(acc)
    try:
        conn.login(acc.get("username") or acc["address"], password)
        typ, data = conn.append(imap_conn.quote(folder), "(\\Seen)", None, raw)
        if typ != "OK":
            raise RuntimeError(f"Ablage abgelehnt: {(data or [b''])[0]!r}"[:200])
        m = _APPENDUID.search(b" ".join(x for x in (data or []) if isinstance(x, bytes)))
        if not m:
            return None
        uidinfo = (int(m.group(1)), int(m.group(2)))
        # Nur übernehmen, wenn der Server die Mail unverändert abgelegt hat (Yahoo schreibt um → andere Größe).
        # Sonst gehört die UID zur Server-Fassung; die archiviert der Abgleich als eigene Mail (sent_link verknüpft).
        conn.select(imap_conn.quote(folder), readonly=True)
        typ, d = conn.uid("FETCH", str(uidinfo[1]), "(RFC822.SIZE)")
        size = re.search(rb"RFC822\.SIZE (\d+)", b" ".join(x if isinstance(x, bytes) else x[0] for x in (d or []) if x))
        return uidinfo if typ == "OK" and size and int(size.group(1)) == len(raw) else None
    finally:
        try:
            conn.logout()
        except Exception:  # noqa: BLE001 - Abmelden darf nichts mehr kaputtmachen
            pass


def _mark_on_server(mid: int, account_id: str, folder: str, uidinfo: tuple[int, int] | None) -> None:
    """Auf dem Server. Mit APPENDUID den Fundort gleich eintragen – sonst ließe sich die Mail bis zum nächsten Abgleich
    nicht verschieben/löschen. Nur wenn die UIDVALIDITY zum Index passt (sonst gehört die UID zu einer anderen Zählung)."""
    with index_db.connect() as c:
        c.execute("UPDATE messages SET deleted_on_server=0 WHERE id=?", (mid,))
        if uidinfo is None:
            return
        f = c.execute("SELECT id, uidvalidity FROM folders WHERE account_id=? AND name=?", (account_id, folder)).fetchone()
        if f and f[1] and f[1] == uidinfo[0]:
            c.execute("INSERT OR IGNORE INTO locations(message_id, folder_id, uid) VALUES (?,?,?)", (mid, f[0], uidinfo[1]))


def deliver(acc: dict, password: str, built, *, allow_internal=frozenset(), open_imap=None) -> dict:
    """Senden. Fehler VOR dem Versand (Grenze, SMTP) werfen; danach nur noch Warnungen im Ergebnis."""
    ratelimit.check(acc["id"])
    res = smtp_send.send(acc, password, built.raw, built.envelope, allow_internal=allow_internal)
    out = {"sent": True, "message_id": built.message_id, "refused": res.get("refused", []),
           "sent_copy": "archive_only", "warning": ""}
    warnings = []
    try:
        ratelimit.record(acc["id"], recipients=len(built.envelope))
    except Exception as e:  # noqa: BLE001 - gesendet ist gesendet
        warnings.append(f"Zählung: {e}")
    provider = (acc.get("imap_host") or "").strip().lower() in SELF_FILING
    folder = _sent_folder(acc["id"])
    mid = None
    if not provider:
        try:
            mid = _archive_copy(acc, built.raw, folder or "Gesendet (lokal)")
        except Exception as e:  # noqa: BLE001
            warnings.append(f"Archiv: {e}")
    if provider:
        out["sent_copy"] = "provider"           # Gmail legt selbst ab; Archiv folgt beim Abgleich
    elif folder and open_imap is not None:
        try:
            uidinfo = _append(acc, password, folder, built.raw, open_imap)
            out["sent_copy"] = "server"
            if mid is not None:
                _mark_on_server(mid, acc["id"], folder, uidinfo)
        except Exception as e:  # noqa: BLE001
            warnings.append(f"Gesendet-Ordner: {e}")
    out["warning"] = "; ".join(w[:200] for w in warnings)
    if warnings:
        log.warning("Mailbox-Versand %s: gesendet, aber %s", acc["id"], out["warning"])
    return out
