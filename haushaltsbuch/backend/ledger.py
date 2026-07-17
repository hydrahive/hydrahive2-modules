from __future__ import annotations

import sqlite3
from datetime import date, datetime
from zoneinfo import ZoneInfo
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from fastapi import status

from hydrahive.api.middleware.auth import AuthPrincipal
from hydrahive.api.middleware.errors import coded
from hydrahive.db.connection import db

from . import audit
from .access import conflict, membership, require_row
from .common import NOW, as_dict, model_values


def _validate_postings(
    conn: sqlite3.Connection,
    household_id: int,
    postings,
    *,
    allow_archived: bool = False,
) -> None:
    if len(postings) < 2 or sum(item.base_amount for item in postings) != 0:
        raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "unbalanced_postings")
    if not any(item.base_amount for item in postings):
        raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "zero_transaction")
    base_currency = conn.execute(
        "SELECT base_currency FROM module_haushaltsbuch_households WHERE id=?",
        (household_id,),
    ).fetchone()[0]
    for posting in postings:
        rate: Decimal | None = None
        if posting.exchange_rate is not None:
            try:
                rate = Decimal(posting.exchange_rate)
                if rate <= 0:
                    raise ValueError
            except (InvalidOperation, ValueError):
                raise coded(
                    status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid_exchange_rate"
                )
        if posting.account_id is not None:
            target = conn.execute(
                "SELECT currency,archived FROM module_haushaltsbuch_accounts WHERE id=? AND household_id=?",
                (posting.account_id, household_id),
            ).fetchone()
            if target is None:
                raise coded(status.HTTP_404_NOT_FOUND, "account_not_found")
            if target["archived"] and not allow_archived:
                raise coded(status.HTTP_409_CONFLICT, "account_archived")
            if posting.currency != target["currency"]:
                raise coded(
                    status.HTTP_422_UNPROCESSABLE_ENTITY, "account_currency_mismatch"
                )
            if posting.currency == base_currency:
                if (
                    posting.original_amount != posting.base_amount
                    or rate is not None
                    or posting.exchange_rate_date is not None
                    or posting.exchange_rate_source is not None
                ):
                    raise coded(
                        status.HTTP_422_UNPROCESSABLE_ENTITY,
                        "base_currency_posting_invalid",
                    )
            else:
                if (
                    rate is None
                    or posting.exchange_rate_date is None
                    or not posting.exchange_rate_source
                ):
                    raise coded(
                        status.HTTP_422_UNPROCESSABLE_ENTITY, "exchange_rate_required"
                    )
                expected = int(
                    (Decimal(posting.original_amount) * rate).quantize(
                        Decimal("1"), rounding=ROUND_HALF_UP
                    )
                )
                if expected != posting.base_amount:
                    raise coded(
                        status.HTTP_422_UNPROCESSABLE_ENTITY,
                        "exchange_rate_amount_mismatch",
                    )
        else:
            target = conn.execute(
                "SELECT archived FROM module_haushaltsbuch_categories WHERE id=? AND household_id=?",
                (posting.category_id, household_id),
            ).fetchone()
            if target is None:
                raise coded(status.HTTP_404_NOT_FOUND, "category_not_found")
            if target["archived"] and not allow_archived:
                raise coded(status.HTTP_409_CONFLICT, "category_archived")
            if (
                posting.currency != base_currency
                or posting.original_amount != posting.base_amount
                or rate is not None
                or posting.exchange_rate_date is not None
                or posting.exchange_rate_source is not None
            ):
                raise coded(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "category_requires_base_currency",
                )
        if (
            posting.member_id is not None
            and conn.execute(
                "SELECT 1 FROM module_haushaltsbuch_members WHERE id=? AND household_id=?",
                (posting.member_id, household_id),
            ).fetchone()
            is None
        ):
            raise coded(status.HTTP_404_NOT_FOUND, "member_not_found")


def _insert(
    conn: sqlite3.Connection,
    household_id: int,
    body,
    actor: str,
    reversal_of: int | None = None,
    *,
    allow_archived: bool = False,
) -> sqlite3.Row:
    _validate_postings(conn, household_id, body.postings, allow_archived=allow_archived)
    value_date = body.value_date or body.booking_date
    cur = conn.execute(
        "INSERT INTO module_haushaltsbuch_transactions"
        "(household_id,booking_date,value_date,counterparty,purpose,note,source,created_by,reversal_of_id) "
        "VALUES(?,?,?,?,?,?,?,?,?)",
        (
            household_id,
            body.booking_date.isoformat(),
            value_date.isoformat(),
            body.counterparty,
            body.purpose,
            body.note,
            body.source,
            actor,
            reversal_of,
        ),
    )
    transaction_id = int(cur.lastrowid)
    conn.executemany(
        "INSERT INTO module_haushaltsbuch_postings"
        "(household_id,transaction_id,account_id,category_id,original_amount,currency,base_amount,exchange_rate,exchange_rate_date,exchange_rate_source,member_id) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (
            (
                household_id,
                transaction_id,
                p.account_id,
                p.category_id,
                p.original_amount,
                p.currency,
                p.base_amount,
                p.exchange_rate,
                p.exchange_rate_date.isoformat() if p.exchange_rate_date else None,
                p.exchange_rate_source,
                p.member_id,
            )
            for p in body.postings
        ),
    )
    from .budgets import add_retroactive_adjustments

    add_retroactive_adjustments(
        conn, household_id, transaction_id, body.booking_date.isoformat()
    )
    return conn.execute(
        "SELECT * FROM module_haushaltsbuch_transactions WHERE id=?", (transaction_id,)
    ).fetchone()


def create_transaction(body, principal: AuthPrincipal) -> dict:
    with db(immediate=True) as conn:
        member = membership(conn, principal)
        row = _insert(conn, member["household_id"], body, principal.user_id)
        audit.record(
            conn,
            member["household_id"],
            principal.user_id,
            "transaction",
            row["id"],
            "create",
            after={
                **as_dict(row),
                "postings": [model_values(p) for p in body.postings],
            },
        )
    return get_transaction(row["id"], principal)


def get_transaction(transaction_id: int, principal: AuthPrincipal) -> dict:
    with db() as conn:
        member = membership(conn, principal)
        row = require_row(
            conn.execute(
                "SELECT * FROM module_haushaltsbuch_transactions WHERE id=? AND household_id=?",
                (transaction_id, member["household_id"]),
            ).fetchone(),
            "transaction_not_found",
        )
        postings = conn.execute(
            "SELECT * FROM module_haushaltsbuch_postings WHERE transaction_id=? ORDER BY id",
            (transaction_id,),
        ).fetchall()
    result = as_dict(row)
    result["postings"] = [as_dict(posting) for posting in postings]
    return result


def list_transactions(
    principal: AuthPrincipal,
    date_from: date | None = None,
    date_to: date | None = None,
    account_id: int | None = None,
    category_id: int | None = None,
    query: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    with db() as conn:
        member = membership(conn, principal)
        sql = "SELECT DISTINCT t.* FROM module_haushaltsbuch_transactions t LEFT JOIN module_haushaltsbuch_postings p ON p.transaction_id=t.id WHERE t.household_id=?"
        params: list = [member["household_id"]]
        if date_from:
            sql += " AND t.booking_date>=?"
            params.append(date_from.isoformat())
        if date_to:
            sql += " AND t.booking_date<=?"
            params.append(date_to.isoformat())
        if account_id:
            sql += " AND p.account_id=?"
            params.append(account_id)
        if category_id:
            sql += " AND p.category_id=?"
            params.append(category_id)
        if query:
            sql += " AND (t.counterparty LIKE ? OR t.purpose LIKE ? OR t.note LIKE ?)"
            term = f"%{query}%"
            params.extend((term, term, term))
        sql += " ORDER BY t.booking_date DESC,t.id DESC LIMIT ? OFFSET ?"
        params.extend((limit, offset))
        rows = conn.execute(sql, params).fetchall()
        result = []
        for row in rows:
            item = as_dict(row)
            postings = conn.execute(
                "SELECT * FROM module_haushaltsbuch_postings WHERE transaction_id=? ORDER BY id",
                (row["id"],),
            ).fetchall()
            item["postings"] = [as_dict(posting) for posting in postings]
            result.append(item)
    return result


def update_metadata(transaction_id: int, body, principal: AuthPrincipal) -> dict:
    with db(immediate=True) as conn:
        member = membership(conn, principal)
        before = require_row(
            conn.execute(
                "SELECT * FROM module_haushaltsbuch_transactions WHERE id=? AND household_id=?",
                (transaction_id, member["household_id"]),
            ).fetchone(),
            "transaction_not_found",
        )
        if (
            before["booking_date"] != body.booking_date.isoformat()
            or before["value_date"] != body.value_date.isoformat()
        ):
            raise coded(status.HTTP_409_CONFLICT, "transaction_dates_immutable")
        cur = conn.execute(
            f"UPDATE module_haushaltsbuch_transactions SET booking_date=?,value_date=?,counterparty=?,purpose=?,note=?,revision=revision+1,updated_at={NOW} WHERE id=? AND household_id=? AND revision=?",
            (
                body.booking_date.isoformat(),
                body.value_date.isoformat(),
                body.counterparty,
                body.purpose,
                body.note,
                transaction_id,
                member["household_id"],
                body.revision,
            ),
        )
        if not cur.rowcount:
            conflict()
        after = conn.execute(
            "SELECT * FROM module_haushaltsbuch_transactions WHERE id=?",
            (transaction_id,),
        ).fetchone()
        audit.record(
            conn,
            member["household_id"],
            principal.user_id,
            "transaction",
            transaction_id,
            "update_metadata",
            before,
            after,
        )
    return as_dict(after)


def reverse_transaction(
    transaction_id: int, revision: int, principal: AuthPrincipal
) -> dict:
    from .models import PostingIn, TransactionCreate

    with db(immediate=True) as conn:
        member = membership(conn, principal)
        original = require_row(
            conn.execute(
                "SELECT * FROM module_haushaltsbuch_transactions WHERE id=? AND household_id=?",
                (transaction_id, member["household_id"]),
            ).fetchone(),
            "transaction_not_found",
        )
        if original["status"] != "posted" or original["revision"] != revision:
            conflict("transaction_already_changed")
        rows = conn.execute(
            "SELECT * FROM module_haushaltsbuch_postings WHERE transaction_id=? ORDER BY id",
            (transaction_id,),
        ).fetchall()
        timezone_name = conn.execute(
            "SELECT timezone FROM module_haushaltsbuch_households WHERE id=?",
            (member["household_id"],),
        ).fetchone()[0]
        reversal_date = datetime.now(ZoneInfo(timezone_name)).date()
        postings = [
            PostingIn(
                account_id=row["account_id"],
                category_id=row["category_id"],
                original_amount=-row["original_amount"],
                currency=row["currency"],
                base_amount=-row["base_amount"],
                exchange_rate=row["exchange_rate"],
                exchange_rate_date=row["exchange_rate_date"],
                exchange_rate_source=row["exchange_rate_source"],
                member_id=row["member_id"],
            )
            for row in rows
        ]
        body = TransactionCreate(
            booking_date=reversal_date,
            value_date=reversal_date,
            counterparty=original["counterparty"],
            purpose=f"Storno: {original['purpose'] or transaction_id}",
            note=None,
            source="manual",
            postings=postings,
        )
        reversal = _insert(
            conn,
            member["household_id"],
            body,
            principal.user_id,
            reversal_of=transaction_id,
            allow_archived=True,
        )
        conn.execute(
            f"UPDATE module_haushaltsbuch_transactions SET status='reversed',revision=revision+1,updated_at={NOW} WHERE id=? AND revision=?",
            (transaction_id, revision),
        )
        audit.record(
            conn,
            member["household_id"],
            principal.user_id,
            "transaction",
            transaction_id,
            "reverse",
            original,
            {"reversal_id": reversal["id"]},
        )
        audit.record(
            conn,
            member["household_id"],
            principal.user_id,
            "transaction",
            reversal["id"],
            "create_reversal",
            after=reversal,
        )
    return get_transaction(reversal["id"], principal)
