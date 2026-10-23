"""Herkunft von Entwürfen, die ein Agent angelegt hat (PLAN-M3b). Ein Agent ändert nur Entwürfe, die in
seinem Projekt (bzw. als Buddy) von einem Agenten angelegt wurden – nie die des Menschen."""
from __future__ import annotations

from hydrahive.db._utils import now_iso
from hydrahive.db.connection import db


def remember(draft_id: str, account_id: str, scope: str) -> None:
    with db() as c:
        c.execute("INSERT OR IGNORE INTO module_mailbox_agent_made(draft_id, account_id, scope, created_at) "
                  "VALUES (?,?,?,?)", (draft_id, account_id, scope, now_iso()))


def owned(draft_id: str, account_id: str, scope: str) -> bool:
    with db() as c:
        return c.execute("SELECT 1 FROM module_mailbox_agent_made WHERE draft_id=? AND account_id=? AND scope=?",
                         (str(draft_id), account_id, scope)).fetchone() is not None


def ids() -> set[str]:
    with db() as c:
        return {r[0] for r in c.execute("SELECT draft_id FROM module_mailbox_agent_made")}


def forget(draft_id: str) -> None:
    with db() as c:
        c.execute("DELETE FROM module_mailbox_agent_made WHERE draft_id=?", (str(draft_id),))
