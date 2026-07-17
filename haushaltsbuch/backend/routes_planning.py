from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Query, status

from hydrahive.db.connection import db

from . import audit, budgets, ledger, recurring
from .access import Principal, membership
from .models import (
    BudgetCreate,
    BudgetUpdate,
    PeriodClose,
    RecurringCreate,
    RecurringUpdate,
)

router = APIRouter()


@router.get("/budgets")
def list_budgets(
    principal: Principal, active_only: bool = True, on_date: date | None = None
) -> list[dict]:
    return budgets.list_budgets(principal, active_only, on_date)


@router.post("/budgets", status_code=status.HTTP_201_CREATED)
def create_budget(body: BudgetCreate, principal: Principal) -> dict:
    return budgets.create_budget(body, principal)


@router.put("/budgets/{budget_id}")
def update_budget(budget_id: int, body: BudgetUpdate, principal: Principal) -> dict:
    return budgets.update_budget(budget_id, body, principal)


@router.post("/budgets/{budget_id}/close")
def close_budget_period(
    budget_id: int, body: PeriodClose, principal: Principal
) -> dict:
    return budgets.close_period(budget_id, body, principal)


@router.get("/recurring")
def list_recurring(principal: Principal, include_inactive: bool = False) -> list[dict]:
    return recurring.list_recurring(principal, include_inactive)


@router.post("/recurring", status_code=status.HTTP_201_CREATED)
def create_recurring(body: RecurringCreate, principal: Principal) -> dict:
    return recurring.create_recurring(body, principal)


@router.put("/recurring/{rule_id}")
def update_recurring(rule_id: int, body: RecurringUpdate, principal: Principal) -> dict:
    return recurring.update_recurring(rule_id, body, principal)


@router.get("/forecast")
def forecast(principal: Principal, days: int = 30) -> dict:
    return recurring.forecast(principal, days)


@router.get("/audit")
def list_audit(
    principal: Principal,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    with db() as conn:
        member = membership(conn, principal)
        rows = conn.execute(
            "SELECT * FROM module_haushaltsbuch_audit_events "
            "WHERE household_id=? ORDER BY id DESC LIMIT ? OFFSET ?",
            (member["household_id"], limit, offset),
        ).fetchall()
    return [audit.decode_row(row) for row in rows]


@router.get("/dashboard")
def dashboard(principal: Principal) -> dict:
    with db() as conn:
        member = membership(conn, principal)
        household_id = member["household_id"]
        timezone_name = conn.execute(
            "SELECT timezone FROM module_haushaltsbuch_households WHERE id=?",
            (household_id,),
        ).fetchone()[0]
        today = datetime.now(ZoneInfo(timezone_name)).date()
        month_start = today.replace(day=1).isoformat()
        total_balance = conn.execute(
            "SELECT COALESCE(SUM(p.base_amount),0) FROM module_haushaltsbuch_postings p "
            "JOIN module_haushaltsbuch_accounts a ON a.id=p.account_id "
            "WHERE p.household_id=? AND a.internal=0",
            (household_id,),
        ).fetchone()[0]
        income, expense = conn.execute(
            "SELECT COALESCE(SUM(CASE WHEN c.kind='income' THEN -p.base_amount ELSE 0 END),0),"
            "COALESCE(SUM(CASE WHEN c.kind='expense' THEN p.base_amount ELSE 0 END),0) "
            "FROM module_haushaltsbuch_postings p "
            "JOIN module_haushaltsbuch_transactions t ON t.id=p.transaction_id "
            "JOIN module_haushaltsbuch_categories c ON c.id=p.category_id "
            "WHERE p.household_id=? AND t.booking_date BETWEEN ? AND ?",
            (household_id, month_start, today.isoformat()),
        ).fetchone()
    current_budgets = budgets.list_budgets(principal, on_date=today)
    current_budgets = [
        item
        for item in current_budgets
        if item["start_date"] <= today.isoformat() <= item["end_date"]
    ]
    forecast_30 = recurring.forecast(principal, 30)
    return {
        "total_balance": int(total_balance),
        "month_income": int(income),
        "month_expense": int(expense),
        "budget_spent": sum(item["spent"] for item in current_budgets),
        "budget_amount": sum(item["available_amount"] for item in current_budgets),
        "upcoming": forecast_30["occurrences"][:10],
        "forecast_30": forecast_30,
        "forecast_90": recurring.forecast(principal, 90),
        "recent_transactions": ledger.list_transactions(principal, limit=10),
    }
