"""Mailkonten (PLAN-M1 Schritt 10): anlegen/ändern/entfernen – nur eigene. Passwort wird vor dem Speichern
getestet, verschlüsselt abgelegt und nie zurückgegeben. Entfernen löscht den Zugang, nie das Archiv.
"""
from __future__ import annotations

import secrets as _rand
import sqlite3

from hydrahive.db._utils import now_iso
from hydrahive.db.connection import db

from . import netcheck, providers, secrets

_PUBLIC = ("id", "label", "address", "sender_name", "auth", "imap_host", "imap_port", "imap_tls", "smtp_host",
           "smtp_port", "smtp_tls", "username", "signature", "status", "status_detail", "created_at", "updated_at")
_EDITABLE = {"label", "sender_name", "imap_host", "imap_port", "imap_tls", "smtp_host", "smtp_port", "smtp_tls",
             "username", "signature", "password"}
TLS = {"ssl", "starttls"}


class NotFound(LookupError):
    pass


class Conflict(ValueError):
    pass


class ConnectError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _owner(user: str) -> str:
    return f"user:{user}"


def _text(v, name: str, max_len: int, *, required: bool = True) -> str:
    if not isinstance(v, str) or (required and not v.strip()) or len(v) > max_len:
        raise ValueError(f"{name}: ungültig")
    return v.strip()


def _validate(d: dict, *, new: bool) -> dict:
    out = {}
    if new:
        providers.domain(d.get("address", ""))
        out["address"] = d["address"].strip().lower()
    for k in ("label", "imap_host", "username"):
        if new or k in d:
            out[k] = _text(d.get(k), k, 200 if k != "imap_host" else 253)
    for k in ("sender_name", "smtp_host"):
        if k in d:
            out[k] = _text(d.get(k) or "", k, 253, required=False)
    if "signature" in d:
        out["signature"] = _text(d.get("signature") or "", "signature", 5000, required=False)
    for k in ("imap_port", "smtp_port"):
        if new or k in d:
            v = d.get(k)
            if not isinstance(v, int) or isinstance(v, bool) or v not in netcheck.MAIL_PORTS:
                raise ValueError(f"{k}: nur Mail-Ports")
            out[k] = v
    for k in ("imap_tls", "smtp_tls"):
        if new or k in d:
            if d.get(k) not in TLS:
                raise ValueError(f"{k}: ssl oder starttls")
            out[k] = d[k]
    if new or "password" in d:
        out["password"] = _text(d.get("password"), "password", 500)
    return out


def redact(text: str, password: str) -> str:
    """Passwort aus Fehlertexten entfernen (manche Server wiederholen die Login-Zeile)."""
    return text.replace(password, "***") if password else text


def allowed_internal_hosts() -> set[str]:
    """Admin-Freigabe für Mailserver im Heimnetz (M1: leer; Einstellung folgt mit der Admin-Seite)."""
    return set()


def _test_login(acc: dict, password: str) -> dict:
    import imaplib
    import ssl

    from . import imap_conn
    try:
        conn = imap_conn.open_connection(acc, allow_internal=allowed_internal_hosts())
    except netcheck.HostBlocked as e:
        raise ConnectError("host_blocked", str(e)) from None
    except ssl.SSLError as e:
        raise ConnectError("tls", f"TLS/Zertifikat: {e}"[:200]) from None
    except OSError as e:
        raise ConnectError("connect", f"Server nicht erreichbar: {e}"[:200]) from None
    try:
        conn.login(acc["username"], password)
        typ, data = conn.list('""', "*")
        return {"folders": len(data or []) if typ == "OK" else 0}
    except imaplib.IMAP4.error as e:
        raise ConnectError("auth", redact(f"Anmeldung fehlgeschlagen: {e}", password)[:200]) from None
    except ssl.SSLError as e:
        raise ConnectError("tls", redact(f"TLS/Zertifikat: {e}", password)[:200]) from None
    except OSError as e:
        raise ConnectError("connect", redact(f"Verbindung abgebrochen: {e}", password)[:200]) from None
    finally:
        try:
            conn.logout()
        except (imaplib.IMAP4.error, OSError):
            pass


def _row(r) -> dict:
    return {k: r[k] for k in _PUBLIC}


def create(user: str, data: dict) -> dict:
    v = _validate(data, new=True)
    v.setdefault("smtp_host", "")
    _test_login(v, v["password"])
    aid, now = _rand.token_hex(12), now_iso()
    with db() as c:
        if c.execute("SELECT 1 FROM module_mailbox_accounts WHERE owner=? AND address=?",
                     (_owner(user), v["address"])).fetchone():
            raise Conflict("Konto mit dieser Adresse gibt es schon")
        c.execute("INSERT INTO module_mailbox_accounts(id, owner, label, address, sender_name, imap_host, imap_port, "
                  "imap_tls, smtp_host, smtp_port, smtp_tls, username, secret, status, created_at, updated_at) "
                  "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?, 'ok', ?, ?)",
                  (aid, _owner(user), v["label"], v["address"], v.get("sender_name", ""), v["imap_host"],
                   v["imap_port"], v["imap_tls"], v["smtp_host"], v["smtp_port"], v["smtp_tls"], v["username"],
                   secrets.seal(aid, v["password"]), now, now))
    return get_own(user, aid)


def list_for(user: str) -> list[dict]:
    with db() as c:
        return [_row(r) for r in c.execute("SELECT * FROM module_mailbox_accounts WHERE owner=? ORDER BY label",
                                           (_owner(user),))]


def get_own(user: str, aid: str) -> dict | None:
    with db() as c:
        r = c.execute("SELECT * FROM module_mailbox_accounts WHERE id=? AND owner=?", (aid, _owner(user))).fetchone()
    return _row(r) if r else None


def all_accounts() -> list[dict]:
    with db() as c:
        return [{**_row(r), "owner": r["owner"]} for r in c.execute("SELECT * FROM module_mailbox_accounts")]


def update(user: str, aid: str, data: dict) -> dict:
    old = get_own(user, aid)
    if not old:
        raise NotFound(aid)
    if "address" in data or set(data) - _EDITABLE:
        raise ValueError("diese Felder lassen sich nicht ändern")
    v = _validate(data, new=False)
    if "password" in v:
        _test_login({**old, **v}, v["password"])
        v["secret"] = secrets.seal(aid, v.pop("password"))
    if v:
        cols = ", ".join(f"{k}=?" for k in v)
        with db() as c:
            c.execute(f"UPDATE module_mailbox_accounts SET {cols}, updated_at=? WHERE id=? AND owner=?",
                      (*v.values(), now_iso(), aid, _owner(user)))
    return get_own(user, aid)


def remove(user: str, aid: str) -> None:
    """Zugang entfernen. Archiv und Index bleiben (Spec §5: nie löschen)."""
    with db() as c:
        if not c.execute("SELECT 1 FROM module_mailbox_accounts WHERE id=? AND owner=?", (aid, _owner(user))).fetchone():
            raise NotFound(aid)
        c.execute("DELETE FROM module_mailbox_sync WHERE account_id=?", (aid,))
        c.execute("DELETE FROM module_mailbox_accounts WHERE id=? AND owner=?", (aid, _owner(user)))


def password_of(aid: str) -> str:
    with db() as c:
        r = c.execute("SELECT secret FROM module_mailbox_accounts WHERE id=?", (aid,)).fetchone()
    if not r:
        raise NotFound(aid)
    return secrets.open_(aid, r[0])


def set_status(aid: str, status: str, detail: str = "") -> None:
    try:
        with db() as c:
            c.execute("UPDATE module_mailbox_accounts SET status=?, status_detail=?, updated_at=? WHERE id=?",
                      (status, (detail or "")[:300], now_iso(), aid))
    except sqlite3.Error:
        pass
