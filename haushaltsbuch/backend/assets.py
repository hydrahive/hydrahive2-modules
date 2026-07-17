from __future__ import annotations

import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import status

from hydrahive.api.middleware.auth import AuthPrincipal
from hydrahive.api.middleware.errors import coded
from hydrahive.db.connection import db

from . import audit
from .access import conflict, membership, require_row
from .common import NOW, as_dict


def _member_owner_valid(conn, household_id: int, member_id: int | None) -> None:
    if (
        member_id is not None
        and conn.execute(
            "SELECT 1 FROM module_haushaltsbuch_members WHERE id=? AND household_id=?",
            (member_id, household_id),
        ).fetchone()
        is None
    ):
        raise coded(status.HTTP_404_NOT_FOUND, "member_not_found")


def list_accounts(
    principal: AuthPrincipal, include_archived: bool = False
) -> list[dict]:
    with db() as conn:
        member = membership(conn, principal)
        rows = conn.execute(
            "SELECT a.*,COALESCE(SUM(p.base_amount),0) AS balance_base FROM module_haushaltsbuch_accounts a "
            "LEFT JOIN module_haushaltsbuch_postings p ON p.account_id=a.id "
            "WHERE a.household_id=? AND a.internal=0 "
            + ("" if include_archived else "AND a.archived=0 ")
            + "GROUP BY a.id ORDER BY a.archived,a.name",
            (member["household_id"],),
        ).fetchall()
    return [as_dict(row) for row in rows]


def create_account(body, principal: AuthPrincipal) -> dict:
    from .ledger import _insert
    from .models import PostingIn, TransactionCreate

    with db(immediate=True) as conn:
        member = membership(conn, principal)
        household_id = member["household_id"]
        _member_owner_valid(conn, household_id, body.owner_member_id)
        try:
            cur = conn.execute(
                "INSERT INTO module_haushaltsbuch_accounts(household_id,name,type,owner_member_id,currency,bank_identifier) VALUES(?,?,?,?,?,?)",
                (
                    household_id,
                    body.name,
                    body.type,
                    body.owner_member_id,
                    body.currency,
                    body.bank_identifier,
                ),
            )
        except sqlite3.IntegrityError:
            raise coded(status.HTTP_409_CONFLICT, "account_name_exists")
        account_id = int(cur.lastrowid)
        row = conn.execute(
            "SELECT * FROM module_haushaltsbuch_accounts WHERE id=?", (account_id,)
        ).fetchone()
        audit.record(
            conn,
            household_id,
            principal.user_id,
            "account",
            account_id,
            "create",
            after=row,
        )
        if body.opening_balance:
            household = conn.execute(
                "SELECT base_currency,timezone FROM module_haushaltsbuch_households WHERE id=?",
                (household_id,),
            ).fetchone()
            if body.currency != household["base_currency"]:
                raise coded(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "fx_opening_balance_requires_transaction",
                )
            equity_id = conn.execute(
                "SELECT id FROM module_haushaltsbuch_accounts WHERE household_id=? AND type='equity' AND internal=1",
                (household_id,),
            ).fetchone()[0]
            opening_date = datetime.now(ZoneInfo(household["timezone"])).date()
            tx = TransactionCreate(
                booking_date=opening_date,
                purpose=f"Eröffnungssaldo {body.name}",
                postings=[
                    PostingIn(
                        account_id=account_id,
                        original_amount=body.opening_balance,
                        currency=body.currency,
                        base_amount=body.opening_balance,
                    ),
                    PostingIn(
                        account_id=equity_id,
                        original_amount=-body.opening_balance,
                        currency=body.currency,
                        base_amount=-body.opening_balance,
                    ),
                ],
            )
            transaction = _insert(conn, household_id, tx, principal.user_id)
            audit.record(
                conn,
                household_id,
                principal.user_id,
                "transaction",
                transaction["id"],
                "opening_balance",
                after=transaction,
            )
    result = as_dict(row)
    result["balance_base"] = body.opening_balance
    return result


def update_account(account_id: int, body, principal: AuthPrincipal) -> dict:
    with db(immediate=True) as conn:
        member = membership(conn, principal)
        household_id = member["household_id"]
        before = require_row(
            conn.execute(
                "SELECT * FROM module_haushaltsbuch_accounts WHERE id=? AND household_id=? AND internal=0",
                (account_id, household_id),
            ).fetchone(),
            "account_not_found",
        )
        _member_owner_valid(conn, household_id, body.owner_member_id)
        try:
            cur = conn.execute(
                f"UPDATE module_haushaltsbuch_accounts SET name=?,type=?,owner_member_id=?,bank_identifier=?,archived=?,revision=revision+1,updated_at={NOW} WHERE id=? AND household_id=? AND revision=?",
                (
                    body.name,
                    body.type,
                    body.owner_member_id,
                    body.bank_identifier,
                    int(body.archived),
                    account_id,
                    household_id,
                    body.revision,
                ),
            )
        except sqlite3.IntegrityError:
            raise coded(status.HTTP_409_CONFLICT, "account_name_exists")
        if not cur.rowcount:
            conflict()
        after = conn.execute(
            "SELECT * FROM module_haushaltsbuch_accounts WHERE id=?", (account_id,)
        ).fetchone()
        audit.record(
            conn,
            household_id,
            principal.user_id,
            "account",
            account_id,
            "update",
            before,
            after,
        )
    return as_dict(after)


def _validate_parent(
    conn, household_id: int, category_id: int | None, parent_id: int | None, kind: str
) -> None:
    seen = {category_id} if category_id else set()
    current = parent_id
    while current is not None:
        if current in seen:
            raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "category_cycle")
        seen.add(current)
        row = conn.execute(
            "SELECT parent_id,kind FROM module_haushaltsbuch_categories WHERE id=? AND household_id=?",
            (current, household_id),
        ).fetchone()
        if row is None:
            raise coded(status.HTTP_404_NOT_FOUND, "parent_category_not_found")
        if row["kind"] != kind:
            raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "category_kind_mismatch")
        current = row["parent_id"]


def list_categories(
    principal: AuthPrincipal, include_archived: bool = False
) -> list[dict]:
    with db() as conn:
        member = membership(conn, principal)
        rows = conn.execute(
            "SELECT * FROM module_haushaltsbuch_categories WHERE household_id=? "
            + ("" if include_archived else "AND archived=0 ")
            + "ORDER BY kind,sort_order,name",
            (member["household_id"],),
        ).fetchall()
    return [as_dict(row) for row in rows]


def create_category(body, principal: AuthPrincipal) -> dict:
    with db(immediate=True) as conn:
        member = membership(conn, principal)
        household_id = member["household_id"]
        _validate_parent(conn, household_id, None, body.parent_id, body.kind)
        try:
            cur = conn.execute(
                "INSERT INTO module_haushaltsbuch_categories(household_id,parent_id,name,kind,icon,color,sort_order) VALUES(?,?,?,?,?,?,?)",
                (
                    household_id,
                    body.parent_id,
                    body.name,
                    body.kind,
                    body.icon,
                    body.color,
                    body.sort_order,
                ),
            )
        except sqlite3.IntegrityError:
            raise coded(status.HTTP_409_CONFLICT, "category_name_exists")
        row = conn.execute(
            "SELECT * FROM module_haushaltsbuch_categories WHERE id=?", (cur.lastrowid,)
        ).fetchone()
        audit.record(
            conn,
            household_id,
            principal.user_id,
            "category",
            row["id"],
            "create",
            after=row,
        )
    return as_dict(row)


def update_category(category_id: int, body, principal: AuthPrincipal) -> dict:
    with db(immediate=True) as conn:
        member = membership(conn, principal)
        household_id = member["household_id"]
        before = require_row(
            conn.execute(
                "SELECT * FROM module_haushaltsbuch_categories WHERE id=? AND household_id=?",
                (category_id, household_id),
            ).fetchone(),
            "category_not_found",
        )
        _validate_parent(conn, household_id, category_id, body.parent_id, body.kind)
        if (
            before["kind"] != body.kind
            and conn.execute(
                "SELECT 1 FROM module_haushaltsbuch_postings WHERE category_id=? LIMIT 1",
                (category_id,),
            ).fetchone()
        ):
            raise coded(status.HTTP_409_CONFLICT, "used_category_kind_immutable")
        try:
            cur = conn.execute(
                f"UPDATE module_haushaltsbuch_categories SET parent_id=?,name=?,kind=?,icon=?,color=?,sort_order=?,archived=?,revision=revision+1,updated_at={NOW} WHERE id=? AND household_id=? AND revision=?",
                (
                    body.parent_id,
                    body.name,
                    body.kind,
                    body.icon,
                    body.color,
                    body.sort_order,
                    int(body.archived),
                    category_id,
                    household_id,
                    body.revision,
                ),
            )
        except sqlite3.IntegrityError:
            raise coded(status.HTTP_409_CONFLICT, "category_name_exists")
        if not cur.rowcount:
            conflict()
        after = conn.execute(
            "SELECT * FROM module_haushaltsbuch_categories WHERE id=?", (category_id,)
        ).fetchone()
        audit.record(
            conn,
            household_id,
            principal.user_id,
            "category",
            category_id,
            "update",
            before,
            after,
        )
    return as_dict(after)
