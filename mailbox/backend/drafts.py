"""Entwürfe (PLAN-M2 Schritt 6). Lokal im Index (Inhalt gehört nicht in die Kern-DB), nur der Ersteller sieht sie.

Kopie im Entwürfe-Ordner des Servers (andere Mailprogramme sehen den Entwurf): erst die neue Kopie ablegen, dann
die alte gezielt über ihre Message-ID entfernen – so geht nie beides verloren. Ohne Entwürfe-Ordner oder bei
Serverfehlern bleibt der Entwurf lokal. Halbe Adressen sind erlaubt (geprüft wird erst beim Senden).
M2: Anhänge werden in Entwürfen nicht gespeichert (sie bleiben bis zum Senden im Schreibfenster).
"""
from __future__ import annotations

import logging
import re
import secrets
from email.message import EmailMessage
from email.policy import SMTP
from email.utils import formatdate, make_msgid

from hydrahive.db._utils import now_iso

from . import actions, addresses, auth_login, imap_conn, index_db

log = logging.getLogger("hydrahive.modules.mailbox")
MODES = frozenset({"new", "reply", "reply_all", "forward"})
_BAD = re.compile(r"[\r\n\x00]")
_LIMITS = {"to": 10_000, "cc": 10_000, "bcc": 10_000, "subject": 998, "body": 1_000_000}
_COLS = {"to": "to_addr", "cc": "cc_addr", "bcc": "bcc_addr", "subject": "subject", "body": "body"}


class DraftError(ValueError):
    pass


def _clean(data: dict) -> dict:
    out = {}
    for k, limit in _LIMITS.items():
        v = data.get(k) or ""
        if not isinstance(v, str) or len(v) > limit or (k != "body" and _BAD.search(v)):
            raise DraftError(f"{k} ungültig")
        out[k] = v
    mode = data.get("mode") or "new"
    if mode not in MODES:
        raise DraftError("mode ungültig")
    ref = data.get("ref_message")
    out.update(mode=mode, ref_message=int(ref) if ref not in (None, "") else None,
               with_attachments=1 if data.get("with_attachments") else 0)
    return out


def _public(r: dict, server: str | None = None) -> dict:
    d = {"id": r["id"], "account_id": r["account_id"], "to": r["to_addr"], "cc": r["cc_addr"], "bcc": r["bcc_addr"],
         "subject": r["subject"], "body": r["body"], "mode": r["mode"], "ref_message": r["ref_message"],
         "with_attachments": bool(r["with_attachments"]), "updated_at": r["updated_at"]}
    if server is not None:
        d["server"] = server
    return d


def _row(user: str, draft_id: str) -> dict | None:
    with index_db.connect() as c:
        r = c.execute("SELECT * FROM drafts WHERE id=? AND owner=?", (str(draft_id), user)).fetchone()
    return dict(r) if r else None


def get(user: str, draft_id: str) -> dict | None:
    r = _row(user, draft_id)
    return _public(r) if r else None


def list_for(user: str) -> list[dict]:
    with index_db.connect() as c:
        rows = c.execute("SELECT * FROM drafts WHERE owner=? ORDER BY updated_at DESC", (user,)).fetchall()
    return [_public(dict(r)) for r in rows]


def _header_addrs(value: str) -> str:
    try:
        return addresses.header(addresses.parse_list(value)) if value.strip() else ""
    except addresses.AddressError:
        return ""                           # halbe Adresse: im Server-Entwurf weglassen, lokal bleibt sie


def _raw(acc: dict, v: dict, msgid: str) -> bytes:
    m = EmailMessage()
    m["From"] = addresses.header([addresses.Recipient(name=acc.get("sender_name") or "", addr=acc["address"])])
    for k, h in (("to", "To"), ("cc", "Cc")):
        if hv := _header_addrs(v[k]):
            m[h] = hv
    m["Subject"] = v["subject"]
    m["Date"] = formatdate(localtime=True)
    m["Message-ID"] = msgid
    m.set_content(v["body"] or "")
    return m.as_bytes(policy=SMTP)


def _drafts_folder(account_id: str) -> str | None:
    return actions._folder_by_role(account_id, "drafts")


def _server_remove(conn, folder: str, msgid: str) -> None:
    if not msgid or not actions._MSGID_OK.match(msgid):
        return
    caps = actions._caps(conn)
    typ, _ = conn.select(imap_conn.quote(folder), readonly=False)
    if typ != "OK":
        return
    typ, data = conn.uid("SEARCH", f'HEADER Message-ID "{msgid}"')
    for uid in (data[0] or b"").decode(errors="replace").split() if typ == "OK" and data else []:
        actions._remove(conn, int(uid), caps)
    actions._leave(conn, caps)


def _sync_server(acc: dict, password: str, open_imap, raw: bytes | None, old_msgid: str) -> str:
    """Neue Kopie ablegen (raw), danach alte entfernen. Gibt "ok" | "local_only" zurück."""
    folder = _drafts_folder(acc["id"])
    if not folder or open_imap is None:
        return "local_only"
    conn = None
    try:
        conn = open_imap(acc)
        auth_login.imap_login(conn, acc, password)
        if raw is not None:
            typ, data = conn.append(imap_conn.quote(folder), "(\\Draft \\Seen)", None, raw)
            if typ != "OK":
                raise RuntimeError(f"Ablage abgelehnt: {(data or [b''])[0]!r}"[:200])
        _server_remove(conn, folder, old_msgid)
        return "ok"
    except Exception as e:  # noqa: BLE001 - der lokale Entwurf ist das Wichtige
        log.warning("Mailbox-Entwurf %s: Server-Kopie nicht aktualisiert: %s", acc["id"], str(e)[:200])
        return "local_only"
    finally:
        if conn is not None:
            try:
                conn.logout()
            except Exception:  # noqa: BLE001
                pass


def save(user: str, acc: dict, data: dict, *, draft_id: str | None = None, password: str = "", open_imap=None) -> dict:
    v = _clean(data)
    old = _row(user, draft_id) if draft_id else None
    if draft_id and not old:
        raise DraftError("Entwurf nicht gefunden")
    if old and old["account_id"] != acc["id"]:
        raise DraftError("Entwurf gehört zu einem anderen Konto")
    did, now = (old["id"] if old else secrets.token_hex(12)), now_iso()
    msgid = make_msgid(domain=acc["address"].rpartition("@")[2])
    server = _sync_server(acc, password, open_imap, _raw(acc, v, msgid), old["server_message_id"] if old else "")
    keep_id = msgid if server == "ok" else (old["server_message_id"] if old else "")
    cols = {_COLS[k]: v[k] for k in _COLS} | {"mode": v["mode"], "ref_message": v["ref_message"],
                                               "with_attachments": v["with_attachments"],
                                               "server_folder": _drafts_folder(acc["id"]) or "",
                                               "server_message_id": keep_id, "updated_at": now}
    with index_db.connect() as c:
        if old:
            c.execute(f"UPDATE drafts SET {', '.join(f'{k}=?' for k in cols)} WHERE id=? AND owner=?",
                      [*cols.values(), did, user])
        else:
            cols |= {"id": did, "account_id": acc["id"], "owner": user, "created_at": now}
            c.execute(f"INSERT INTO drafts({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                      list(cols.values()))
    return _public(_row(user, did), server)


def delete(user: str, draft_id: str, acc: dict, *, password: str = "", open_imap=None) -> bool:
    """Entwurf löschen (auch nach dem Senden). Fremde/unbekannte → False."""
    old = _row(user, draft_id)
    if not old or old["account_id"] != acc["id"]:
        return False
    _sync_server(acc, password, open_imap, None, old["server_message_id"])
    with index_db.connect() as c:
        c.execute("DELETE FROM drafts WHERE id=? AND owner=?", (old["id"], user))
    return True
