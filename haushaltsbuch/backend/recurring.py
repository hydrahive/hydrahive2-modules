from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import status

from hydrahive.api.middleware.auth import AuthPrincipal
from hydrahive.api.middleware.errors import coded
from hydrahive.db.connection import db

from . import audit
from .access import conflict, membership, require_row
from .common import NOW, as_dict


def _targets_exist(
    conn, household_id: int, account_id: int, category_id: int, kind: str
) -> None:
    account = conn.execute(
        "SELECT 1 FROM module_haushaltsbuch_accounts WHERE id=? AND household_id=? AND archived=0 AND internal=0",
        (account_id, household_id),
    ).fetchone()
    category = conn.execute(
        "SELECT kind FROM module_haushaltsbuch_categories WHERE id=? AND household_id=? AND archived=0",
        (category_id, household_id),
    ).fetchone()
    if account is None:
        raise coded(status.HTTP_404_NOT_FOUND, "account_not_found")
    if category is None:
        raise coded(status.HTTP_404_NOT_FOUND, "category_not_found")
    if category["kind"] != kind:
        raise coded(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "recurring_category_kind_mismatch"
        )


def next_occurrence(
    current: date, frequency: str, interval: int, anchor_day: int | None
) -> date:
    if frequency == "daily":
        return current + timedelta(days=interval)
    if frequency == "weekly":
        return current + timedelta(weeks=interval)
    if frequency == "monthly":
        month_index = current.year * 12 + current.month - 1 + interval
        year, month0 = divmod(month_index, 12)
        month = month0 + 1
        day = min(anchor_day or current.day, calendar.monthrange(year, month)[1])
        return date(year, month, day)
    year = current.year + interval
    day = min(current.day, calendar.monthrange(year, current.month)[1])
    return date(year, current.month, day)


def list_recurring(
    principal: AuthPrincipal, include_inactive: bool = False
) -> list[dict]:
    with db() as conn:
        member = membership(conn, principal)
        rows = conn.execute(
            "SELECT * FROM module_haushaltsbuch_recurring_rules WHERE household_id=? "
            + ("" if include_inactive else "AND status<>'inactive' ")
            + "ORDER BY next_due_date,id",
            (member["household_id"],),
        ).fetchall()
        timezone_name = conn.execute(
            "SELECT timezone FROM module_haushaltsbuch_households WHERE id=?",
            (member["household_id"],),
        ).fetchone()[0]
    today = datetime.now(ZoneInfo(timezone_name)).date()
    result = [as_dict(row) for row in rows]
    for item in result:
        item["overdue"] = (
            item["status"] == "confirmed" and item["next_due_date"] < today.isoformat()
        )
    return result


def create_recurring(body, principal: AuthPrincipal) -> dict:
    with db(immediate=True) as conn:
        member = membership(conn, principal)
        household_id = member["household_id"]
        _targets_exist(conn, household_id, body.account_id, body.category_id, body.kind)
        cur = conn.execute(
            "INSERT INTO module_haushaltsbuch_recurring_rules(household_id,kind,account_id,category_id,frequency,interval_count,next_due_date,end_date,anchor_day,amount,tolerance,counterparty,cancellation_notice_days,note,status,confidence) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                household_id,
                body.kind,
                body.account_id,
                body.category_id,
                body.frequency,
                body.interval_count,
                body.next_due_date.isoformat(),
                body.end_date.isoformat() if body.end_date else None,
                body.anchor_day,
                body.amount,
                body.tolerance,
                body.counterparty,
                body.cancellation_notice_days,
                body.note,
                body.status,
                body.confidence,
            ),
        )
        row = conn.execute(
            "SELECT * FROM module_haushaltsbuch_recurring_rules WHERE id=?",
            (cur.lastrowid,),
        ).fetchone()
        audit.record(
            conn,
            household_id,
            principal.user_id,
            "recurring",
            row["id"],
            "create",
            after=row,
        )
    return as_dict(row)


def update_recurring(rule_id: int, body, principal: AuthPrincipal) -> dict:
    with db(immediate=True) as conn:
        member = membership(conn, principal)
        household_id = member["household_id"]
        before = require_row(
            conn.execute(
                "SELECT * FROM module_haushaltsbuch_recurring_rules WHERE id=? AND household_id=?",
                (rule_id, household_id),
            ).fetchone(),
            "recurring_not_found",
        )
        if before["revision"] != body.revision:
            conflict()
        _targets_exist(conn, household_id, body.account_id, body.category_id, body.kind)
        conn.execute(
            f"UPDATE module_haushaltsbuch_recurring_rules SET kind=?,account_id=?,category_id=?,frequency=?,interval_count=?,next_due_date=?,end_date=?,anchor_day=?,amount=?,tolerance=?,counterparty=?,cancellation_notice_days=?,note=?,status=?,confidence=?,revision=revision+1,updated_at={NOW} WHERE id=?",
            (
                body.kind,
                body.account_id,
                body.category_id,
                body.frequency,
                body.interval_count,
                body.next_due_date.isoformat(),
                body.end_date.isoformat() if body.end_date else None,
                body.anchor_day,
                body.amount,
                body.tolerance,
                body.counterparty,
                body.cancellation_notice_days,
                body.note,
                body.status,
                body.confidence,
                rule_id,
            ),
        )
        after = conn.execute(
            "SELECT * FROM module_haushaltsbuch_recurring_rules WHERE id=?", (rule_id,)
        ).fetchone()
        audit.record(
            conn,
            household_id,
            principal.user_id,
            "recurring",
            rule_id,
            "update",
            before,
            after,
        )
    return as_dict(after)


def forecast(principal: AuthPrincipal, days: int) -> dict:
    if days not in (30, 90, 365):
        raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "forecast_horizon_invalid")
    with db() as conn:
        member = membership(conn, principal)
        household_id = member["household_id"]
        timezone_name = conn.execute(
            "SELECT timezone FROM module_haushaltsbuch_households WHERE id=?",
            (household_id,),
        ).fetchone()[0]
        today = datetime.now(ZoneInfo(timezone_name)).date()
        until = today + timedelta(days=days)
        rows = conn.execute(
            "SELECT * FROM module_haushaltsbuch_recurring_rules WHERE household_id=? AND status='confirmed' ORDER BY id",
            (household_id,),
        ).fetchall()
        balance = conn.execute(
            "SELECT COALESCE(SUM(p.base_amount),0) FROM module_haushaltsbuch_postings p JOIN module_haushaltsbuch_accounts a ON a.id=p.account_id WHERE p.household_id=? AND a.internal=0",
            (household_id,),
        ).fetchone()[0]
    occurrences = []
    net = 0
    for row in rows:
        due = date.fromisoformat(row["next_due_date"])
        end = date.fromisoformat(row["end_date"]) if row["end_date"] else None
        while due <= until and (end is None or due <= end):
            if due >= today:
                effect = row["amount"] if row["kind"] == "income" else -row["amount"]
                net += effect
                occurrences.append(
                    {
                        "rule_id": row["id"],
                        "due_date": due.isoformat(),
                        "amount": row["amount"],
                        "effect": effect,
                        "kind": row["kind"],
                        "counterparty": row["counterparty"],
                    }
                )
            due = next_occurrence(
                due, row["frequency"], row["interval_count"], row["anchor_day"]
            )
    occurrences.sort(key=lambda item: (item["due_date"], item["rule_id"]))
    running = int(balance)
    warnings = []
    for item in occurrences:
        running += item["effect"]
        item["projected_balance"] = running
        if running < 0:
            warnings.append({"date": item["due_date"], "projected_balance": running})
    return {
        "days": days,
        "opening_balance": int(balance),
        "net_change": net,
        "closing_balance": int(balance) + net,
        "occurrences": occurrences,
        "warnings": warnings,
    }
