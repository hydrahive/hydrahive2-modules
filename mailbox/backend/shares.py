"""Freigabe eines Mailkontos für Agenten (Spec §7, PLAN-M3a).

Ziel ``project:<id>``: Agenten in diesem Projekt dürfen das Konto nutzen – aber nur in Läufen eines Nutzers, der
Mitglied des Projekts ist (System-Admin: immer). Ziel ``buddy``: nur ohne Projekt und nur für den Besitzer selbst.
Freigeben darf nur der Besitzer des Kontos, und nur in Projekte, in denen er selbst Mitglied ist.
"""
from __future__ import annotations

import re

from hydrahive.db._utils import now_iso
from hydrahive.db.connection import db

from . import accounts

LEVELS = ("read", "draft")              # M4: send
RANK = {"read": 1, "draft": 2}
BUDDY = "buddy"
_PROJECT = re.compile(r"^project:([0-9a-f-]{8,64})$")


class NotFound(LookupError):
    pass


def _project(project_id: str) -> dict | None:
    from hydrahive.projects._config_io import get
    return get(project_id)


def _role(username: str) -> str:
    from hydrahive.api.middleware.users import get_by_username
    return (get_by_username(username) or {}).get("role", "user")


def _member(username: str, project_id: str) -> bool:
    from hydrahive.projects import _members_model
    p = _project(project_id)
    if p is None:
        return False
    return _role(username) == "admin" or _members_model.is_member(p, username)


def _check_target(user: str, target: str) -> str:
    if target == BUDDY:
        return target
    m = _PROJECT.match(target or "")
    if not m or not _member(user, m.group(1)):
        raise ValueError("Ziel ungültig: unbekanntes Projekt oder du bist dort kein Mitglied")
    return target


def put(user: str, aid: str, target: str, level: str = "read") -> dict:
    if not accounts.get_own(user, aid):
        raise NotFound(aid)
    if level not in LEVELS:
        raise ValueError(f"Stufe ungültig (erlaubt: {', '.join(LEVELS)})")
    target = _check_target(user, target)
    with db() as c:
        c.execute("INSERT INTO module_mailbox_shares(account_id, target, level, created_by, created_at) "
                  "VALUES (?,?,?,?,?) ON CONFLICT(account_id, target) DO UPDATE SET level=excluded.level",
                  (aid, target, level, user, now_iso()))
    return next(s for s in list_for(user, aid) if s["target"] == target)


def list_for(user: str, aid: str) -> list[dict]:
    if not accounts.get_own(user, aid):
        raise NotFound(aid)
    with db() as c:
        rows = c.execute("SELECT target, level, created_by, created_at FROM module_mailbox_shares "
                         "WHERE account_id=? ORDER BY target", (aid,)).fetchall()
    return [dict(r) for r in rows]


def remove(user: str, aid: str, target: str) -> bool:
    if not accounts.get_own(user, aid):
        raise NotFound(aid)
    with db() as c:
        return c.execute("DELETE FROM module_mailbox_shares WHERE account_id=? AND target=?",
                         (aid, target)).rowcount > 0


def owner_of(aid: str) -> str | None:
    """Benutzername des Kontobesitzers (Entwürfe eines Agenten gehören ihm und erscheinen in seinem Webmail)."""
    with db() as c:
        r = c.execute("SELECT owner FROM module_mailbox_accounts WHERE id=?", (aid,)).fetchone()
    return r[0].removeprefix("user:") if r and r[0].startswith("user:") else None


def scope_of(project_id: str | None) -> str:
    return f"project:{project_id}" if project_id else BUDDY


def visible(user: str, project_id: str | None, need: str = "read") -> dict[str, str]:
    """Konto-ID → Adresse aller Konten, die ein Werkzeuglauf von ``user`` in ``project_id`` mit mindestens Stufe
    ``need`` nutzen darf."""
    allowed = tuple(lvl for lvl, r in RANK.items() if r >= RANK[need])
    if project_id:
        if not _member(user, project_id):
            return {}
        sql = ("SELECT a.id, a.address FROM module_mailbox_shares s JOIN module_mailbox_accounts a "
               "ON a.id=s.account_id WHERE s.target=?")
        args: tuple = (f"project:{project_id}",)
    else:
        sql = ("SELECT a.id, a.address FROM module_mailbox_shares s JOIN module_mailbox_accounts a "
               "ON a.id=s.account_id WHERE s.target=? AND a.owner=?")
        args = (BUDDY, f"user:{user}")
    sql += f" AND s.level IN ({','.join('?' * len(allowed))})"
    with db() as c:
        return {r["id"]: r["address"] for r in c.execute(sql + " ORDER BY a.address", (*args, *allowed))}
