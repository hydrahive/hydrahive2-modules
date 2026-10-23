"""Protokoll der Agenten-Aktionen (Spec §4 audit). Nie Mailinhalt: nur wer, wo, Werkzeug, Mail-ID, Ergebnis.
Ein Fehler beim Protokollieren darf das Werkzeug nicht scheitern lassen, wird aber geloggt."""
from __future__ import annotations

import logging
import sqlite3

from hydrahive.db._utils import now_iso
from hydrahive.db.connection import db

log = logging.getLogger("hydrahive.modules.mailbox")


def record(ctx, tool: str, result: str, *, account_id: str = "", message_id: int | None = None) -> None:
    try:
        with db() as c:
            c.execute("INSERT INTO module_mailbox_audit(at, username, project_id, agent_id, account_id, tool, "
                      "message_id, result) VALUES (?,?,?,?,?,?,?,?)",
                      (now_iso(), ctx.user_id or "", ctx.project_id or "", ctx.agent_id or "", account_id, tool,
                       message_id, result))
    except sqlite3.Error as e:
        log.warning("mailbox: Protokoll nicht geschrieben (%s, %s): %s", tool, result, e)


def for_account(account_id: str, limit: int = 100) -> list[dict]:
    with db() as c:
        rows = c.execute("SELECT at, username, project_id, tool, message_id, result FROM module_mailbox_audit "
                         "WHERE account_id=? ORDER BY id DESC LIMIT ?", (account_id, int(limit))).fetchall()
    return [dict(r) for r in rows]
