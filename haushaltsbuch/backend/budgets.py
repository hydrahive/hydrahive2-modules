from __future__ import annotations

import calendar
import sqlite3
from datetime import date, datetime, timezone

from fastapi import status

from hydrahive.api.middleware.auth import AuthPrincipal
from hydrahive.api.middleware.errors import coded
from hydrahive.db.connection import db

from . import audit
from .access import conflict, membership, require_row
from .common import NOW, as_dict


def _validate_scope(
    conn,
    household_id: int,
    category_id: int | None,
    start: str,
    end: str,
    exclude_id: int | None = None,
) -> None:
    if category_id is not None:
        row = conn.execute(
            "SELECT kind FROM module_haushaltsbuch_categories WHERE id=? AND household_id=?",
            (category_id, household_id),
        ).fetchone()
        if row is None:
            raise coded(status.HTTP_404_NOT_FOUND, "category_not_found")
        if row["kind"] != "expense":
            raise coded(
                status.HTTP_422_UNPROCESSABLE_ENTITY, "budget_requires_expense_category"
            )
    sql = "SELECT 1 FROM module_haushaltsbuch_budgets WHERE household_id=? AND active=1 AND ((category_id=? ) OR (category_id IS NULL AND ? IS NULL)) AND start_date<=? AND end_date>=?"
    params: list = [household_id, category_id, category_id, end, start]
    if exclude_id is not None:
        sql += " AND id<>?"
        params.append(exclude_id)
    if conn.execute(sql, params).fetchone():
        raise coded(status.HTTP_409_CONFLICT, "budget_period_overlap")


def _spent(
    conn, household_id: int, category_id: int | None, start: str, end: str
) -> int:
    if category_id is None:
        row = conn.execute(
            "SELECT COALESCE(SUM(p.base_amount),0) FROM module_haushaltsbuch_postings p "
            "JOIN module_haushaltsbuch_transactions t ON t.id=p.transaction_id "
            "JOIN module_haushaltsbuch_categories c ON c.id=p.category_id "
            "WHERE p.household_id=? AND c.kind='expense' AND t.booking_date BETWEEN ? AND ?",
            (household_id, start, end),
        ).fetchone()
    else:
        row = conn.execute(
            "WITH RECURSIVE scope(id) AS (SELECT ? UNION ALL SELECT c.id FROM module_haushaltsbuch_categories c JOIN scope s ON c.parent_id=s.id WHERE c.household_id=?) "
            "SELECT COALESCE(SUM(p.base_amount),0) FROM module_haushaltsbuch_postings p JOIN module_haushaltsbuch_transactions t ON t.id=p.transaction_id "
            "WHERE p.household_id=? AND p.category_id IN (SELECT id FROM scope) AND t.booking_date BETWEEN ? AND ?",
            (category_id, household_id, household_id, start, end),
        ).fetchone()
    return int(row[0])


def _window(row: sqlite3.Row, on_date: date) -> tuple[str, str]:
    budget_start = date.fromisoformat(row["start_date"])
    budget_end = date.fromisoformat(row["end_date"])
    if row["type"] in ("monthly", "monthly_rollover"):
        period_start = on_date.replace(day=1)
    elif row["type"] == "yearly":
        period_start = on_date.replace(month=1, day=1)
    else:
        period_start = budget_start
    return max(budget_start, period_start).isoformat(), min(
        budget_end, on_date
    ).isoformat()


def _period_rows(conn: sqlite3.Connection, budget_id: int, before: str | None = None):
    condition = "AND bp.end_date<? " if before is not None else ""
    params = (budget_id, before) if before is not None else (budget_id,)
    return conn.execute(
        "SELECT bp.*,COALESCE(SUM(ba.amount),0) AS adjustment_amount "
        "FROM module_haushaltsbuch_budget_periods bp "
        "LEFT JOIN module_haushaltsbuch_budget_adjustments ba ON ba.budget_period_id=bp.id "
        f"WHERE bp.budget_id=? {condition}"
        "GROUP BY bp.id ORDER BY bp.start_date",
        params,
    ).fetchall()


def _effective_periods(
    conn: sqlite3.Connection,
    budget_id: int,
    before: str | None = None,
    *,
    carry: bool,
) -> list[dict]:
    result = []
    effective_rollover = 0
    for row in _period_rows(conn, budget_id, before):
        item = as_dict(row)
        base_allocation = int(item["base_allocation_amount"])
        item["effective_spent_amount"] = (
            item["spent_amount"] + item["adjustment_amount"]
        )
        item["effective_allocated_amount"] = base_allocation + (
            effective_rollover if carry else 0
        )
        item["effective_rollover_amount"] = max(
            item["effective_allocated_amount"] - item["effective_spent_amount"], 0
        )
        effective_rollover = item["effective_rollover_amount"]
        result.append(item)
    return result


def _periods(conn: sqlite3.Connection, budget: sqlite3.Row) -> list[dict]:
    return _effective_periods(
        conn, budget["id"], carry=budget["type"] == "monthly_rollover"
    )


def _incoming_rollover(conn: sqlite3.Connection, budget_id: int, before: str) -> int:
    periods = _effective_periods(conn, budget_id, before, carry=True)
    return periods[-1]["effective_rollover_amount"] if periods else 0


def list_budgets(
    principal: AuthPrincipal, active_only: bool = True, on_date: date | None = None
) -> list[dict]:
    on_date = on_date or date.today()
    with db() as conn:
        member = membership(conn, principal)
        rows = conn.execute(
            "SELECT * FROM module_haushaltsbuch_budgets WHERE household_id=? "
            + ("AND active=1 " if active_only else "")
            + "ORDER BY start_date,id",
            (member["household_id"],),
        ).fetchall()
        result = []
        for row in rows:
            item = as_dict(row)
            start, end = _window(row, on_date)
            item["spent"] = (
                _spent(conn, member["household_id"], row["category_id"], start, end)
                if end >= start
                else 0
            )
            incoming = (
                _incoming_rollover(conn, row["id"], start)
                if row["type"] == "monthly_rollover"
                else 0
            )
            item["available_amount"] = row["amount"] + incoming
            item["remaining"] = item["available_amount"] - item["spent"]
            item["warning"] = bool(
                item["available_amount"]
                and item["spent"] * 100
                >= item["available_amount"] * row["warning_threshold"]
            )
            item["periods"] = _periods(conn, row)
            result.append(item)
    return result


def create_budget(body, principal: AuthPrincipal) -> dict:
    with db(immediate=True) as conn:
        member = membership(conn, principal)
        household_id = member["household_id"]
        start, end = body.start_date.isoformat(), body.end_date.isoformat()
        _validate_scope(conn, household_id, body.category_id, start, end)
        cur = conn.execute(
            "INSERT INTO module_haushaltsbuch_budgets(household_id,category_id,type,amount,start_date,end_date,warning_threshold) VALUES(?,?,?,?,?,?,?)",
            (
                household_id,
                body.category_id,
                body.type,
                body.amount,
                start,
                end,
                body.warning_threshold,
            ),
        )
        row = conn.execute(
            "SELECT * FROM module_haushaltsbuch_budgets WHERE id=?", (cur.lastrowid,)
        ).fetchone()
        audit.record(
            conn,
            household_id,
            principal.user_id,
            "budget",
            row["id"],
            "create",
            after=row,
        )
    return as_dict(row)


def update_budget(budget_id: int, body, principal: AuthPrincipal) -> dict:
    with db(immediate=True) as conn:
        member = membership(conn, principal)
        household_id = member["household_id"]
        before = require_row(
            conn.execute(
                "SELECT * FROM module_haushaltsbuch_budgets WHERE id=? AND household_id=?",
                (budget_id, household_id),
            ).fetchone(),
            "budget_not_found",
        )
        if before["revision"] != body.revision:
            conflict()
        if body.active:
            _validate_scope(
                conn,
                household_id,
                body.category_id,
                body.start_date.isoformat(),
                body.end_date.isoformat(),
                budget_id,
            )
        conn.execute(
            f"UPDATE module_haushaltsbuch_budgets SET category_id=?,type=?,amount=?,start_date=?,end_date=?,warning_threshold=?,active=?,revision=revision+1,updated_at={NOW} WHERE id=?",
            (
                body.category_id,
                body.type,
                body.amount,
                body.start_date.isoformat(),
                body.end_date.isoformat(),
                body.warning_threshold,
                int(body.active),
                budget_id,
            ),
        )
        after = conn.execute(
            "SELECT * FROM module_haushaltsbuch_budgets WHERE id=?", (budget_id,)
        ).fetchone()
        audit.record(
            conn,
            household_id,
            principal.user_id,
            "budget",
            budget_id,
            "update",
            before,
            after,
        )
    return as_dict(after)


def _validate_close_window(
    conn: sqlite3.Connection, budget: sqlite3.Row, start: date, end: date
) -> None:
    budget_start = date.fromisoformat(budget["start_date"])
    budget_end = date.fromisoformat(budget["end_date"])
    if start < budget_start or end > budget_end or end < start:
        raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid_budget_period")
    previous = conn.execute(
        "SELECT end_date FROM module_haushaltsbuch_budget_periods "
        "WHERE budget_id=? ORDER BY end_date DESC LIMIT 1",
        (budget["id"],),
    ).fetchone()
    expected_start = (
        date.fromisoformat(previous["end_date"]) + date.resolution
        if previous
        else budget_start
    )
    if start != expected_start:
        raise coded(status.HTTP_409_CONFLICT, "budget_period_not_chronological")
    if budget["type"] in ("monthly", "monthly_rollover"):
        expected_end = date(
            start.year, start.month, calendar.monthrange(start.year, start.month)[1]
        )
        if end != min(expected_end, budget_end):
            raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid_monthly_period")
    elif budget["type"] == "yearly":
        expected_end = date(start.year, 12, 31)
        if end != min(expected_end, budget_end):
            raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid_yearly_period")


def close_period(budget_id: int, body, principal: AuthPrincipal) -> dict:
    with db(immediate=True) as conn:
        member = membership(conn, principal)
        household_id = member["household_id"]
        budget = require_row(
            conn.execute(
                "SELECT * FROM module_haushaltsbuch_budgets WHERE id=? AND household_id=?",
                (budget_id, household_id),
            ).fetchone(),
            "budget_not_found",
        )
        if budget["revision"] != body.revision:
            conflict()
        _validate_close_window(conn, budget, body.start_date, body.end_date)
        start, end = body.start_date.isoformat(), body.end_date.isoformat()
        if conn.execute(
            "SELECT 1 FROM module_haushaltsbuch_budget_periods "
            "WHERE budget_id=? AND start_date<=? AND end_date>=?",
            (budget_id, end, start),
        ).fetchone():
            raise coded(status.HTTP_409_CONFLICT, "budget_period_overlap")
        spent = _spent(conn, household_id, budget["category_id"], start, end)
        incoming = (
            _incoming_rollover(conn, budget_id, start)
            if budget["type"] == "monthly_rollover"
            else 0
        )
        allocated = budget["amount"] + incoming
        rollover = (
            max(allocated - spent, 0)
            if budget["type"] in ("monthly_rollover", "reserve")
            else 0
        )
        try:
            cur = conn.execute(
                "INSERT INTO module_haushaltsbuch_budget_periods(household_id,budget_id,start_date,end_date,base_allocation_amount,allocated_amount,spent_amount,rollover_amount,closed_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    household_id,
                    budget_id,
                    start,
                    end,
                    budget["amount"],
                    allocated,
                    spent,
                    rollover,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        except sqlite3.IntegrityError:
            raise coded(status.HTTP_409_CONFLICT, "budget_period_already_closed")
        conn.execute(
            f"UPDATE module_haushaltsbuch_budgets SET revision=revision+1,updated_at={NOW} WHERE id=?",
            (budget_id,),
        )
        row = conn.execute(
            "SELECT * FROM module_haushaltsbuch_budget_periods WHERE id=?",
            (cur.lastrowid,),
        ).fetchone()
        audit.record(
            conn,
            household_id,
            principal.user_id,
            "budget",
            budget_id,
            "close_period",
            before=budget,
            after=row,
        )
    return as_dict(row)


def add_retroactive_adjustments(
    conn: sqlite3.Connection, household_id: int, transaction_id: int, booking_date: str
) -> None:
    postings = conn.execute(
        "SELECT category_id,base_amount FROM module_haushaltsbuch_postings WHERE transaction_id=? AND category_id IS NOT NULL",
        (transaction_id,),
    ).fetchall()
    for posting in postings:
        periods = conn.execute(
            "WITH RECURSIVE ancestors(id) AS (SELECT ? UNION ALL SELECT c.parent_id FROM module_haushaltsbuch_categories c JOIN ancestors a ON c.id=a.id WHERE c.parent_id IS NOT NULL) "
            "SELECT bp.id FROM module_haushaltsbuch_budget_periods bp JOIN module_haushaltsbuch_budgets b ON b.id=bp.budget_id "
            "WHERE bp.household_id=? AND ? BETWEEN bp.start_date AND bp.end_date AND (b.category_id IS NULL OR b.category_id IN (SELECT id FROM ancestors))",
            (posting["category_id"], household_id, booking_date),
        ).fetchall()
        conn.executemany(
            "INSERT INTO module_haushaltsbuch_budget_adjustments(household_id,budget_period_id,transaction_id,amount) VALUES(?,?,?,?)",
            (
                (household_id, period["id"], transaction_id, posting["base_amount"])
                for period in periods
            ),
        )
