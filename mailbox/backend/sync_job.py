"""Abgleich-Job (PLAN-M1 Schritt 10): alle Konten nacheinander; IMAP blockiert → je Konto in einem Thread.

Sperre je Konto in module_mailbox_sync (kein Doppellauf zwischen Job und „Jetzt abrufen“); hängt ein Lauf länger
als STALE_SECONDS (Absturz), darf ein neuer übernehmen. Fehler eines Kontos landen als Status, die anderen laufen weiter.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from hydrahive.db._utils import now_iso
from hydrahive.db.connection import db

from . import accounts, fetch, imap_conn

STALE_SECONDS = 6 * 3600
log = logging.getLogger("hydrahive.modules.mailbox")


def _open(acc: dict):
    return imap_conn.open_connection(acc, allow_internal=accounts.allowed_internal_hosts())


def _claim(aid: str) -> bool:
    limit = (datetime.now(timezone.utc) - timedelta(seconds=STALE_SECONDS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    with db() as c:
        c.execute("INSERT OR IGNORE INTO module_mailbox_sync(account_id) VALUES (?)", (aid,))
        cur = c.execute("UPDATE module_mailbox_sync SET running=1, started_at=?, last_error='' WHERE account_id=? AND "
                        "(running=0 OR started_at IS NULL OR started_at < ?)", (now_iso(), aid, limit))
        return cur.rowcount == 1


def _release(aid: str, error: str, counts: dict | None = None) -> None:
    """Lauf beenden. Zähler schreibt _write_progress während des Laufs (hier nicht noch einmal addieren)."""
    with db() as c:
        c.execute("UPDATE module_mailbox_sync SET running=0, finished_at=?, last_error=? WHERE account_id=?",
                  (now_iso(), (error or "")[:300], aid))


def _write_progress(aid: str, done: int, folders_done: int, folders_total: int) -> None:
    with db() as c:
        c.execute("UPDATE module_mailbox_sync SET messages_done=?, folders_done=?, folders_total=? WHERE account_id=?",
                  (done, folders_done, folders_total, aid))


def progress(aid: str) -> dict:
    with db() as c:
        r = c.execute("SELECT * FROM module_mailbox_sync WHERE account_id=?", (aid,)).fetchone()
    return dict(r) if r else {}


def _redact(text: str, aid: str) -> str:
    """Passwort nie in Status/Log, auch wenn ein Server die Login-Zeile in die Fehlermeldung schreibt."""
    try:
        pw = accounts.password_of(aid)
    except Exception:  # noqa: BLE001 - ohne lesbares Passwort gibt es nichts zu schwärzen
        return text
    return accounts.redact(text, pw)


def _sync_one(acc: dict) -> dict:
    """messages_done = alle bisher archivierten Mails des Kontos (Stand vor dem Lauf + neue dieses Laufs)."""
    base = progress(acc["id"]).get("messages_done") or 0

    def cb(c: dict) -> None:
        _write_progress(acc["id"], base + c["new"], c["folders"], c["folders_total"])
    conn = _open(acc)
    try:
        return fetch.sync_account(acc, conn, login=(acc["username"], accounts.password_of(acc["id"])),
                                  on_progress=cb)   # fetch meldet nach jedem Ordner – auch nach dem letzten
    finally:
        try:
            conn.logout()
        except Exception:  # noqa: BLE001
            pass


async def _run(acc: dict) -> bool:
    if not _claim(acc["id"]):
        return False
    error, counts = "", None
    try:
        counts = await asyncio.to_thread(_sync_one, acc)
        accounts.set_status(acc["id"], "ok", "")
    except fetch.AuthFailed as e:
        error = _redact(str(e), acc["id"])
        accounts.set_status(acc["id"], "auth_failed", error)
    except Exception as e:  # noqa: BLE001 - ein Konto darf den Job nie stoppen
        error = _redact(f"{type(e).__name__}: {e}", acc["id"])
        accounts.set_status(acc["id"], "error", error)
        log.warning("Mailbox-Abgleich %s: %s", acc["id"], error)
    finally:
        _release(acc["id"], error, counts)
    return True


async def job() -> None:
    for acc in accounts.all_accounts():
        await _run(acc)


async def sync_now(user: str, aid: str) -> bool:
    acc = accounts.get_own(user, aid)
    if not acc:
        return False
    return await _run(acc)
