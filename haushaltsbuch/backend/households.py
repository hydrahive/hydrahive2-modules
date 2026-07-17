from __future__ import annotations

import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

from fastapi import status

from hydrahive.api.middleware.auth import AuthPrincipal
from hydrahive.api.middleware.errors import coded
from hydrahive.api.middleware.users import get_by_username
from hydrahive.db.connection import db

from . import audit
from .access import conflict, membership, owner_membership, require_row
from .common import NOW, as_dict, model_values
from .models import HouseholdCreate

_DEFAULT_CATEGORIES = (
    ("Gehalt", "income", "WalletCards", "#2E7D32", 10),
    ("Sonstige Einnahmen", "income", "CirclePlus", "#558B2F", 20),
    ("Wohnen", "expense", "House", "#1565C0", 10),
    ("Lebensmittel", "expense", "ShoppingCart", "#EF6C00", 20),
    ("Mobilität", "expense", "Car", "#6A1B9A", 30),
    ("Freizeit", "expense", "PartyPopper", "#00838F", 40),
    ("Gesundheit", "expense", "HeartPulse", "#C62828", 50),
    ("Sonstiges", "expense", "MoreHorizontal", "#546E7A", 60),
)


def create_household(body: HouseholdCreate, principal: AuthPrincipal) -> dict:
    values = model_values(body)
    with db(immediate=True) as conn:
        if conn.execute(
            "SELECT 1 FROM module_haushaltsbuch_members WHERE user_id=?",
            (principal.user_id,),
        ).fetchone():
            raise coded(status.HTTP_409_CONFLICT, "already_in_household")
        cur = conn.execute(
            "INSERT INTO module_haushaltsbuch_households(name,base_currency,timezone,owner_user_id) VALUES(?,?,?,?)",
            (body.name, body.base_currency, body.timezone, principal.user_id),
        )
        household_id = int(cur.lastrowid)
        conn.execute(
            "INSERT INTO module_haushaltsbuch_members(household_id,user_id,username,role) VALUES(?,?,?,'owner')",
            (household_id, principal.user_id, principal.username),
        )
        conn.execute(
            "INSERT INTO module_haushaltsbuch_accounts(household_id,name,type,currency,internal) VALUES(?,?,'equity',?,1)",
            (household_id, "Eröffnungssalden", body.base_currency),
        )
        conn.execute(
            "INSERT INTO module_haushaltsbuch_accounts(household_id,name,type,currency,internal) VALUES(?,?,'rounding',?,1)",
            (household_id, "Rundungsdifferenzen", body.base_currency),
        )
        if body.create_default_categories:
            conn.executemany(
                "INSERT INTO module_haushaltsbuch_categories(household_id,name,kind,icon,color,sort_order) VALUES(?,?,?,?,?,?)",
                ((household_id, *item) for item in _DEFAULT_CATEGORIES),
            )
        row = conn.execute(
            "SELECT * FROM module_haushaltsbuch_households WHERE id=?", (household_id,)
        ).fetchone()
        audit.record(
            conn,
            household_id,
            principal.user_id,
            "household",
            household_id,
            "create",
            after=values,
        )
    return as_dict(row)


def get_household(principal: AuthPrincipal) -> dict:
    with db() as conn:
        member = membership(conn, principal)
        household = conn.execute(
            "SELECT * FROM module_haushaltsbuch_households WHERE id=?",
            (member["household_id"],),
        ).fetchone()
        members = conn.execute(
            "SELECT id,user_id,username,role,revision,joined_at FROM module_haushaltsbuch_members WHERE household_id=? ORDER BY role DESC,id",
            (member["household_id"],),
        ).fetchall()
    result = as_dict(household)
    result["current_role"] = member["role"]
    result["members"] = [as_dict(row) for row in members]
    return result


def update_household(body, principal: AuthPrincipal) -> dict:
    with db(immediate=True) as conn:
        member = owner_membership(conn, principal)
        before = conn.execute(
            "SELECT * FROM module_haushaltsbuch_households WHERE id=?",
            (member["household_id"],),
        ).fetchone()
        if before["base_currency"] != body.base_currency:
            raise coded(status.HTTP_409_CONFLICT, "base_currency_immutable")
        cur = conn.execute(
            f"UPDATE module_haushaltsbuch_households SET name=?,base_currency=?,timezone=?,revision=revision+1,updated_at={NOW} WHERE id=? AND revision=?",
            (
                body.name,
                body.base_currency,
                body.timezone,
                member["household_id"],
                body.revision,
            ),
        )
        if not cur.rowcount:
            conflict()
        after = conn.execute(
            "SELECT * FROM module_haushaltsbuch_households WHERE id=?",
            (member["household_id"],),
        ).fetchone()
        audit.record(
            conn,
            member["household_id"],
            principal.user_id,
            "household",
            member["household_id"],
            "update",
            before,
            after,
        )
    return as_dict(after)


def add_member(username: str, principal: AuthPrincipal) -> dict:
    target = get_by_username(username)
    if target is None or target["username"] != username:
        raise coded(status.HTTP_404_NOT_FOUND, "user_not_found")
    with db(immediate=True) as conn:
        owner = owner_membership(conn, principal)
        try:
            cur = conn.execute(
                "INSERT INTO module_haushaltsbuch_members(household_id,user_id,username,role) VALUES(?,?,?,'member')",
                (owner["household_id"], target["user_id"], target["username"]),
            )
        except sqlite3.IntegrityError:
            raise coded(status.HTTP_409_CONFLICT, "already_in_household")
        row = conn.execute(
            "SELECT * FROM module_haushaltsbuch_members WHERE id=?", (cur.lastrowid,)
        ).fetchone()
        audit.record(
            conn,
            owner["household_id"],
            principal.user_id,
            "membership",
            row["id"],
            "create",
            after=row,
        )
    return as_dict(row)


def remove_member(member_id: int, revision: int, principal: AuthPrincipal) -> None:
    with db(immediate=True) as conn:
        owner = owner_membership(conn, principal)
        target = require_row(
            conn.execute(
                "SELECT * FROM module_haushaltsbuch_members WHERE id=? AND household_id=?",
                (member_id, owner["household_id"]),
            ).fetchone(),
            "member_not_found",
        )
        if target["role"] == "owner":
            raise coded(status.HTTP_409_CONFLICT, "cannot_remove_owner")
        conn.execute(
            "UPDATE module_haushaltsbuch_accounts SET owner_member_id=NULL WHERE owner_member_id=? AND household_id=?",
            (member_id, owner["household_id"]),
        )
        conn.execute(
            "UPDATE module_haushaltsbuch_postings SET member_id=NULL WHERE member_id=? AND household_id=?",
            (member_id, owner["household_id"]),
        )
        cur = conn.execute(
            "DELETE FROM module_haushaltsbuch_members WHERE id=? AND revision=?",
            (member_id, revision),
        )
        if not cur.rowcount:
            conflict()
        audit.record(
            conn,
            owner["household_id"],
            principal.user_id,
            "membership",
            member_id,
            "delete",
            before=target,
        )


def transfer_ownership(member_id: int, revision: int, principal: AuthPrincipal) -> dict:
    with db(immediate=True) as conn:
        owner = owner_membership(conn, principal)
        target = require_row(
            conn.execute(
                "SELECT * FROM module_haushaltsbuch_members WHERE id=? AND household_id=?",
                (member_id, owner["household_id"]),
            ).fetchone(),
            "member_not_found",
        )
        if target["role"] == "owner" or target["revision"] != revision:
            conflict()
        conn.execute(
            "UPDATE module_haushaltsbuch_members SET role='member',revision=revision+1 WHERE id=?",
            (owner["id"],),
        )
        conn.execute(
            "UPDATE module_haushaltsbuch_members SET role='owner',revision=revision+1 WHERE id=?",
            (member_id,),
        )
        conn.execute(
            f"UPDATE module_haushaltsbuch_households SET owner_user_id=?,revision=revision+1,updated_at={NOW} WHERE id=?",
            (target["user_id"], owner["household_id"]),
        )
        after = conn.execute(
            "SELECT * FROM module_haushaltsbuch_members WHERE id=?", (member_id,)
        ).fetchone()
        audit.record(
            conn,
            owner["household_id"],
            principal.user_id,
            "membership",
            member_id,
            "transfer_ownership",
            target,
            after,
        )
    return as_dict(after)


def create_invite(hours: int, principal: AuthPrincipal) -> dict:
    code = secrets.token_urlsafe(32)
    digest = hashlib.sha256(code.encode()).hexdigest()
    expires = datetime.now(timezone.utc) + timedelta(hours=hours)
    with db(immediate=True) as conn:
        owner = owner_membership(conn, principal)
        cur = conn.execute(
            "INSERT INTO module_haushaltsbuch_invites(household_id,token_hash,expires_at,created_by) VALUES(?,?,?,?)",
            (owner["household_id"], digest, expires.isoformat(), principal.user_id),
        )
        row = conn.execute(
            "SELECT * FROM module_haushaltsbuch_invites WHERE id=?", (cur.lastrowid,)
        ).fetchone()
        audit.record(
            conn,
            owner["household_id"],
            principal.user_id,
            "invite",
            row["id"],
            "create",
            after={"expires_at": row["expires_at"]},
        )
    result = as_dict(row)
    result.pop("token_hash")
    result["code"] = code
    return result


def list_invites(principal: AuthPrincipal) -> list[dict]:
    with db() as conn:
        owner = owner_membership(conn, principal)
        rows = conn.execute(
            "SELECT id,household_id,expires_at,status,created_by,accepted_by,revision,created_at,accepted_at FROM module_haushaltsbuch_invites WHERE household_id=? ORDER BY id DESC",
            (owner["household_id"],),
        ).fetchall()
    return [as_dict(row) for row in rows]


def accept_invite(code: str, principal: AuthPrincipal) -> dict:
    digest = hashlib.sha256(code.encode()).hexdigest()
    now = datetime.now(timezone.utc).isoformat()
    with db(immediate=True) as conn:
        if conn.execute(
            "SELECT 1 FROM module_haushaltsbuch_members WHERE user_id=?",
            (principal.user_id,),
        ).fetchone():
            raise coded(status.HTTP_409_CONFLICT, "already_in_household")
        invite = conn.execute(
            "SELECT * FROM module_haushaltsbuch_invites WHERE token_hash=? AND status='pending'",
            (digest,),
        ).fetchone()
        if invite is None:
            raise coded(status.HTTP_404_NOT_FOUND, "invite_not_found")
        if invite["expires_at"] <= now:
            raise coded(status.HTTP_410_GONE, "invite_expired")
        conn.execute(
            "UPDATE module_haushaltsbuch_invites SET status='accepted',accepted_by=?,accepted_at=?,revision=revision+1 WHERE id=? AND status='pending'",
            (principal.user_id, now, invite["id"]),
        )
        cur = conn.execute(
            "INSERT INTO module_haushaltsbuch_members(household_id,user_id,username,role) VALUES(?,?,?,'member')",
            (invite["household_id"], principal.user_id, principal.username),
        )
        member = conn.execute(
            "SELECT * FROM module_haushaltsbuch_members WHERE id=?", (cur.lastrowid,)
        ).fetchone()
        audit.record(
            conn,
            invite["household_id"],
            principal.user_id,
            "invite",
            invite["id"],
            "accept",
            before=invite,
            after={"accepted_by": principal.user_id},
        )
        audit.record(
            conn,
            invite["household_id"],
            principal.user_id,
            "membership",
            member["id"],
            "create",
            after=member,
        )
    return as_dict(member)


def revoke_invite(invite_id: int, revision: int, principal: AuthPrincipal) -> None:
    with db(immediate=True) as conn:
        owner = owner_membership(conn, principal)
        before = require_row(
            conn.execute(
                "SELECT * FROM module_haushaltsbuch_invites WHERE id=? AND household_id=?",
                (invite_id, owner["household_id"]),
            ).fetchone(),
            "invite_not_found",
        )
        cur = conn.execute(
            "UPDATE module_haushaltsbuch_invites SET status='revoked',revision=revision+1 WHERE id=? AND household_id=? AND revision=? AND status='pending'",
            (invite_id, owner["household_id"], revision),
        )
        if not cur.rowcount:
            conflict()
        audit.record(
            conn,
            owner["household_id"],
            principal.user_id,
            "invite",
            invite_id,
            "revoke",
            before=before,
            after={"status": "revoked"},
        )


def export_household(principal: AuthPrincipal) -> dict:
    tables = (
        "households",
        "members",
        "invites",
        "accounts",
        "categories",
        "transactions",
        "postings",
        "budgets",
        "budget_periods",
        "budget_adjustments",
        "recurring_rules",
        "audit_events",
    )
    with db() as conn:
        owner = owner_membership(conn, principal)
        result = {
            "schema_version": 1,
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }
        for table in tables:
            rows = conn.execute(
                f"SELECT * FROM module_haushaltsbuch_{table} WHERE household_id=?",
                (owner["household_id"],),
            ).fetchall()
            result[table] = [as_dict(row) for row in rows]
        for invite in result["invites"]:
            invite.pop("token_hash", None)
    return result


def delete_household(name: str, principal: AuthPrincipal) -> None:
    with db(immediate=True) as conn:
        owner = owner_membership(conn, principal)
        household = conn.execute(
            "SELECT * FROM module_haushaltsbuch_households WHERE id=?",
            (owner["household_id"],),
        ).fetchone()
        if household["name"] != name:
            raise coded(status.HTTP_409_CONFLICT, "confirmation_mismatch")
        conn.execute(
            "DELETE FROM module_haushaltsbuch_households WHERE id=?",
            (owner["household_id"],),
        )
