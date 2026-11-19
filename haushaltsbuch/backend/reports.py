"""Auswertungen (Phase 1, reine Lese-Aggregate).

Fünf Aggregate für das Haushaltsbuch: Cashflow, Vermögen (net worth),
Kategorien-Verteilung, Budget-Verlauf und feste/variable Kosten. Alle
Geldwerte bleiben Integer-Minor-Units (`base_amount`), Prozentanteile werden
als Basispunkte (Integer, 10000 = 100 %) über das Largest-Remainder-Verfahren
verteilt. Keine Floats, keine Division mit `/` auf Geldbeträge.

Der API-Vertrag steht in PHASE1-REPORTS-CONTRACT.md (Orchestrierung V9).
"""

from __future__ import annotations

import calendar
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import status

from hydrahive.api.middleware.auth import AuthPrincipal
from hydrahive.api.middleware.errors import coded
from hydrahive.db.connection import db

from . import budgets as budgets_module
from .access import membership

_RANGE_MONTHS = {"3": 3, "6": 6, "12": 12, "24": 24}
_MAX_MONTHS = 120


def _add_months(value: date, delta: int) -> date:
    month_index = value.year * 12 + (value.month - 1) + delta
    year, month0 = divmod(month_index, 12)
    return date(year, month0 + 1, 1)


def _month_key(value: date) -> str:
    return f"{value.year:04d}-{value.month:02d}"


def _month_end(month_start: date) -> date:
    last_day = calendar.monthrange(month_start.year, month_start.month)[1]
    return month_start.replace(day=last_day)


def _month_range(start_month: date, end_month: date) -> list[date]:
    months = []
    current = start_month
    while current <= end_month:
        months.append(current)
        current = _add_months(current, 1)
    return months


def _household_today(conn, household_id: int) -> date:
    timezone_name = conn.execute(
        "SELECT timezone FROM module_haushaltsbuch_households WHERE id=?",
        (household_id,),
    ).fetchone()[0]
    return datetime.now(ZoneInfo(timezone_name)).date()


def _household_currency(conn, household_id: int) -> str:
    return conn.execute(
        "SELECT base_currency FROM module_haushaltsbuch_households WHERE id=?",
        (household_id,),
    ).fetchone()[0]


def _resolve_window(
    conn, household_id: int, range_param: str, today: date
) -> tuple[date, date]:
    """Start- und Endmonat (jeweils 1. des Monats) für den Report-Zeitraum.

    Feste Bereiche (3/6/12/24): rückwärts vom aktuellen Monat, inklusive.
    `all`: ab dem Monat der ersten Buchung, ohne Buchungen ab dem Monat der
    Haushaltsgründung (`households.created_at`). In jedem Fall höchstens
    120 Monate (Deckel für `all`, feste Bereiche sind ohnehin <= 24).
    """
    current_month = today.replace(day=1)
    if range_param in _RANGE_MONTHS:
        months = _RANGE_MONTHS[range_param]
        return _add_months(current_month, -(months - 1)), current_month
    if range_param != "all":
        raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid_range")
    first_booking = conn.execute(
        "SELECT MIN(booking_date) FROM module_haushaltsbuch_transactions WHERE household_id=?",
        (household_id,),
    ).fetchone()[0]
    if first_booking:
        start_month = date.fromisoformat(first_booking).replace(day=1)
    else:
        created_at = conn.execute(
            "SELECT created_at FROM module_haushaltsbuch_households WHERE id=?",
            (household_id,),
        ).fetchone()[0]
        start_month = date.fromisoformat(created_at[:10]).replace(day=1)
    earliest_allowed = _add_months(current_month, -(_MAX_MONTHS - 1))
    if start_month < earliest_allowed:
        start_month = earliest_allowed
    return start_month, current_month


def _largest_remainder_shares(amounts: Sequence[int], total: int) -> list[int]:
    """Verteilt 10000 Basispunkte exakt proportional zu `amounts` über `total`.

    Largest-Remainder-Verfahren, ausschließlich Integer-Arithmetik: zuerst
    Floor-Anteil je Betrag (`//`), danach wird die Rundungs-Differenz an die
    Einträge mit dem größten Rest verteilt, damit die Summe exakt 10000 ist.
    """
    n = len(amounts)
    if total <= 0 or n == 0:
        return [0] * n
    shares: list[int] = []
    remainders: list[int] = []
    for amount in amounts:
        numerator = amount * 10000
        share, remainder = divmod(numerator, total)
        shares.append(share)
        remainders.append(remainder)
    deficit = 10000 - sum(shares)
    order = sorted(range(n), key=lambda i: (-remainders[i], i))
    for i in order[:deficit]:
        shares[i] += 1
    return shares


def _envelope(
    report: str,
    range_param: str,
    currency: str,
    start_month: date,
    end_month: date,
    rows: list[dict],
    totals: dict,
) -> dict:
    return {
        "report": report,
        "range": range_param,
        "currency": currency,
        "start_month": _month_key(start_month),
        "end_month": _month_key(end_month),
        "rows": rows,
        "totals": totals,
    }


def cashflow(principal: AuthPrincipal, range_param: str = "12") -> dict:
    """Einnahmen/Ausgaben je Monat, wie `routes_planning.dashboard()`."""
    with db() as conn:
        member = membership(conn, principal)
        household_id = member["household_id"]
        currency = _household_currency(conn, household_id)
        today = _household_today(conn, household_id)
        start_month, end_month = _resolve_window(conn, household_id, range_param, today)
        months = _month_range(start_month, end_month)
        raw = conn.execute(
            "SELECT strftime('%Y-%m', t.booking_date) AS month,"
            " COALESCE(SUM(CASE WHEN c.kind='income' THEN -p.base_amount ELSE 0 END),0) AS income,"
            " COALESCE(SUM(CASE WHEN c.kind='expense' THEN p.base_amount ELSE 0 END),0) AS expense"
            " FROM module_haushaltsbuch_postings p"
            " JOIN module_haushaltsbuch_transactions t ON t.id=p.transaction_id"
            " JOIN module_haushaltsbuch_categories c ON c.id=p.category_id"
            " WHERE p.household_id=? AND t.booking_date BETWEEN ? AND ?"
            " GROUP BY month",
            (household_id, start_month.isoformat(), _month_end(end_month).isoformat()),
        ).fetchall()
    by_month = {row["month"]: (int(row["income"]), int(row["expense"])) for row in raw}
    rows = []
    total_income = total_expense = 0
    for month in months:
        key = _month_key(month)
        income, expense = by_month.get(key, (0, 0))
        total_income += income
        total_expense += expense
        rows.append(
            {"month": key, "income": income, "expense": expense, "net": income - expense}
        )
    totals = {
        "income": total_income,
        "expense": total_expense,
        "net": total_income - total_expense,
    }
    return _envelope("cashflow", range_param, currency, start_month, end_month, rows, totals)


def net_worth(
    principal: AuthPrincipal,
    range_param: str = "12",
    extra_month_values: Sequence[Mapping[str, int]] | None = None,
) -> dict:
    """Kumulierter Saldo aller nicht-internen Konten, je Monatsende.

    `extra_month_values` ist der Erweiterungspunkt für spätere Zusatzquellen
    (z. B. Phase 3/4 Krypto-Bewertung): eine Liste von Mappings `{"YYYY-MM": delta}`,
    die auf den jeweiligen Monatsdelta addiert werden. Default leer -> keine
    Wirkung, Phase 1 hat keine Krypto-Logik.
    """
    extra_sources = extra_month_values or []
    with db() as conn:
        member = membership(conn, principal)
        household_id = member["household_id"]
        currency = _household_currency(conn, household_id)
        today = _household_today(conn, household_id)
        start_month, end_month = _resolve_window(conn, household_id, range_param, today)
        months = _month_range(start_month, end_month)
        opening = conn.execute(
            "SELECT COALESCE(SUM(p.base_amount),0) FROM module_haushaltsbuch_postings p"
            " JOIN module_haushaltsbuch_accounts a ON a.id=p.account_id"
            " JOIN module_haushaltsbuch_transactions t ON t.id=p.transaction_id"
            " WHERE p.household_id=? AND a.internal=0 AND t.booking_date<?",
            (household_id, start_month.isoformat()),
        ).fetchone()[0]
        raw = conn.execute(
            "SELECT strftime('%Y-%m', t.booking_date) AS month,"
            " COALESCE(SUM(p.base_amount),0) AS delta"
            " FROM module_haushaltsbuch_postings p"
            " JOIN module_haushaltsbuch_accounts a ON a.id=p.account_id"
            " JOIN module_haushaltsbuch_transactions t ON t.id=p.transaction_id"
            " WHERE p.household_id=? AND a.internal=0 AND t.booking_date BETWEEN ? AND ?"
            " GROUP BY month",
            (household_id, start_month.isoformat(), _month_end(end_month).isoformat()),
        ).fetchall()
    deltas = {row["month"]: int(row["delta"]) for row in raw}
    extra_by_month: dict[str, int] = {}
    for source in extra_sources:
        for key, value in dict(source).items():
            extra_by_month[key] = extra_by_month.get(key, 0) + int(value)
    running = int(opening)
    rows = []
    for month in months:
        key = _month_key(month)
        running += deltas.get(key, 0) + extra_by_month.get(key, 0)
        rows.append({"month": key, "balance": running})
    start_balance = int(opening)
    end_balance = rows[-1]["balance"] if rows else start_balance
    totals = {
        "start_balance": start_balance,
        "end_balance": end_balance,
        "change": end_balance - start_balance,
    }
    return _envelope("net-worth", range_param, currency, start_month, end_month, rows, totals)


def _has_children(conn, household_id: int, category_id: int) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM module_haushaltsbuch_categories WHERE parent_id=? AND household_id=? LIMIT 1",
            (category_id, household_id),
        ).fetchone()
        is not None
    )


def _direct_amount(
    conn, household_id: int, category_id: int, start_date: str, end_date: str
) -> int:
    row = conn.execute(
        "SELECT COALESCE(SUM(p.base_amount),0) FROM module_haushaltsbuch_postings p"
        " JOIN module_haushaltsbuch_transactions t ON t.id=p.transaction_id"
        " WHERE p.household_id=? AND p.category_id=? AND t.booking_date BETWEEN ? AND ?",
        (household_id, category_id, start_date, end_date),
    ).fetchone()
    return int(row[0])


def categories(
    principal: AuthPrincipal, range_param: str = "12", parent_id: int | None = None
) -> dict:
    """Ausgaben-Verteilung je Hauptkategorie, optional Drilldown auf Unterkategorien.

    Beträge je Kategorie summieren rekursiv die gesamte Unterkategorie-Kette
    (über `budgets._spent`, dieselbe Hilfe wie der Budget-Verlauf). Ohne
    `parent_id` werden nur Hauptkategorien (parent_id IS NULL) mit Betrag > 0
    gezeigt. Mit `parent_id` kommen die direkten Unterkategorien dazu, plus
    ggf. eine Zeile für Beträge, die direkt auf der Hauptkategorie gebucht
    wurden (`"<Name> (direkt)"`, has_children=false).
    """
    with db() as conn:
        member = membership(conn, principal)
        household_id = member["household_id"]
        currency = _household_currency(conn, household_id)
        today = _household_today(conn, household_id)
        start_month, end_month = _resolve_window(conn, household_id, range_param, today)
        start_date = start_month.isoformat()
        end_date = _month_end(end_month).isoformat()
        rows_data: list[dict] = []
        if parent_id is not None:
            parent = conn.execute(
                "SELECT id,name FROM module_haushaltsbuch_categories WHERE id=? AND household_id=?",
                (parent_id, household_id),
            ).fetchone()
            if parent is None:
                raise coded(status.HTTP_404_NOT_FOUND, "category_not_found")
            children = conn.execute(
                "SELECT id,name FROM module_haushaltsbuch_categories WHERE parent_id=? AND household_id=?"
                " ORDER BY sort_order,name",
                (parent_id, household_id),
            ).fetchall()
            for child in children:
                amount = budgets_module._spent(
                    conn, household_id, child["id"], start_date, end_date
                )
                if amount <= 0:
                    continue
                rows_data.append(
                    {
                        "category_id": child["id"],
                        "name": child["name"],
                        "amount": amount,
                        "has_children": _has_children(conn, household_id, child["id"]),
                    }
                )
            direct_amount = _direct_amount(conn, household_id, parent_id, start_date, end_date)
            if direct_amount > 0:
                rows_data.append(
                    {
                        "category_id": parent_id,
                        "name": f"{parent['name']} (direkt)",
                        "amount": direct_amount,
                        "has_children": False,
                    }
                )
        else:
            top = conn.execute(
                "SELECT id,name FROM module_haushaltsbuch_categories"
                " WHERE parent_id IS NULL AND household_id=? AND kind='expense'"
                " ORDER BY sort_order,name",
                (household_id,),
            ).fetchall()
            for cat in top:
                amount = budgets_module._spent(conn, household_id, cat["id"], start_date, end_date)
                if amount <= 0:
                    continue
                rows_data.append(
                    {
                        "category_id": cat["id"],
                        "name": cat["name"],
                        "amount": amount,
                        "has_children": _has_children(conn, household_id, cat["id"]),
                    }
                )
    rows_data.sort(key=lambda item: (-item["amount"], item["category_id"]))
    total_expense = sum(item["amount"] for item in rows_data)
    shares = _largest_remainder_shares([item["amount"] for item in rows_data], total_expense)
    rows = [
        {**item, "share_bp": share} for item, share in zip(rows_data, shares, strict=True)
    ]
    totals = {"expense": total_expense}
    return _envelope("categories", range_param, currency, start_month, end_month, rows, totals)


def budgets(principal: AuthPrincipal, range_param: str = "12") -> dict:
    """Soll/Ist je aktivem Budget und je Monat, in dem das Budget gilt.

    Nutzt dieselben Hilfen wie `budgets.list_budgets`: `_window` für das
    gültige Zeitfenster je Monat, `_spent` für die Ist-Summe, `_incoming_rollover`
    für übertragene Rollover-Beträge. Für nicht-monatliche Budgets
    (`yearly`/`one_time`/`reserve`) wächst das Fenster mit jedem Monat
    (`_window` liefert start=Budgetstart, end=min(Budgetende, Monatsende)):
    `planned` ist dort der volle Fensterbetrag, `spent` kumuliert bis
    Monatsende, wie in der Hilfe selbst.
    """
    with db() as conn:
        member = membership(conn, principal)
        household_id = member["household_id"]
        currency = _household_currency(conn, household_id)
        today = _household_today(conn, household_id)
        start_month, end_month = _resolve_window(conn, household_id, range_param, today)
        months = _month_range(start_month, end_month)
        budget_rows = conn.execute(
            "SELECT * FROM module_haushaltsbuch_budgets WHERE household_id=? AND active=1"
            " ORDER BY start_date,id",
            (household_id,),
        ).fetchall()
        names: dict[int, str] = {}
        for budget_row in budget_rows:
            if budget_row["category_id"] is not None:
                cat = conn.execute(
                    "SELECT name FROM module_haushaltsbuch_categories WHERE id=?",
                    (budget_row["category_id"],),
                ).fetchone()
                names[budget_row["id"]] = cat["name"] if cat else "Unbekannt"
            else:
                names[budget_row["id"]] = "Gesamtbudget"
        rows: list[dict] = []
        for budget_row in budget_rows:
            for month in months:
                start, end = budgets_module._window(budget_row, _month_end(month))
                if end < start:
                    continue
                spent = budgets_module._spent(
                    conn, household_id, budget_row["category_id"], start, end
                )
                incoming = (
                    budgets_module._incoming_rollover(conn, budget_row["id"], start)
                    if budget_row["type"] == "monthly_rollover"
                    else 0
                )
                planned = budget_row["amount"] + incoming
                remaining = planned - spent
                used_bp = (spent * 10000) // planned if planned > 0 else 0
                rows.append(
                    {
                        "budget_id": budget_row["id"],
                        "name": names[budget_row["id"]],
                        "month": _month_key(month),
                        "planned": planned,
                        "spent": spent,
                        "remaining": remaining,
                        "used_bp": used_bp,
                    }
                )
    last_month_key = _month_key(months[-1]) if months else None
    last_rows = [row for row in rows if row["month"] == last_month_key]
    totals = {
        "planned": sum(row["planned"] for row in last_rows),
        "spent": sum(row["spent"] for row in last_rows),
    }
    return _envelope("budgets", range_param, currency, start_month, end_month, rows, totals)


def fixed_costs(principal: AuthPrincipal, range_param: str = "12") -> dict:
    """Feste vs. variable Ausgaben je Monat.

    Heuristik "fest": eine Ausgaben-Buchung zählt als fest, wenn eine
    wiederkehrende Ausgabe-Regel (`recurring_rules`) existiert mit
    - derselben `category_id`, UND
    - Regel ohne `counterparty` ODER die Buchung hat einen `counterparty`,
      der case-insensitiv mit dem der Regel übereinstimmt, UND
    - Regel-Status `confirmed`, ODER Status `inactive` und im Monat der
      Buchung noch gültig (`end_date` leer oder >= Buchungsdatum).
    `variable` ist der Rest (`total - fixed`), `fixed_bp` der Integer-Anteil
    (`//`, kein Largest-Remainder nötig, da nur ein Wert je Monat).
    """
    with db() as conn:
        member = membership(conn, principal)
        household_id = member["household_id"]
        currency = _household_currency(conn, household_id)
        today = _household_today(conn, household_id)
        start_month, end_month = _resolve_window(conn, household_id, range_param, today)
        months = _month_range(start_month, end_month)
        start_date = start_month.isoformat()
        end_date = _month_end(end_month).isoformat()
        raw_total = conn.execute(
            "SELECT strftime('%Y-%m', t.booking_date) AS month,"
            " COALESCE(SUM(p.base_amount),0) AS total"
            " FROM module_haushaltsbuch_postings p"
            " JOIN module_haushaltsbuch_transactions t ON t.id=p.transaction_id"
            " JOIN module_haushaltsbuch_categories c ON c.id=p.category_id"
            " WHERE p.household_id=? AND c.kind='expense' AND t.booking_date BETWEEN ? AND ?"
            " GROUP BY month",
            (household_id, start_date, end_date),
        ).fetchall()
        raw_fixed = conn.execute(
            "SELECT strftime('%Y-%m', t.booking_date) AS month,"
            " COALESCE(SUM(p.base_amount),0) AS fixed"
            " FROM module_haushaltsbuch_postings p"
            " JOIN module_haushaltsbuch_transactions t ON t.id=p.transaction_id"
            " JOIN module_haushaltsbuch_categories c ON c.id=p.category_id"
            " WHERE p.household_id=? AND c.kind='expense' AND t.booking_date BETWEEN ? AND ?"
            " AND EXISTS ("
            "   SELECT 1 FROM module_haushaltsbuch_recurring_rules r"
            "   WHERE r.household_id=p.household_id AND r.category_id=p.category_id"
            "     AND (r.counterparty IS NULL OR"
            "          (t.counterparty IS NOT NULL AND LOWER(r.counterparty)=LOWER(t.counterparty)))"
            "     AND (r.status='confirmed' OR"
            "          (r.status='inactive' AND (r.end_date IS NULL OR r.end_date>=t.booking_date)))"
            " )"
            " GROUP BY month",
            (household_id, start_date, end_date),
        ).fetchall()
    total_by_month = {row["month"]: int(row["total"]) for row in raw_total}
    fixed_by_month = {row["month"]: int(row["fixed"]) for row in raw_fixed}
    rows = []
    total_fixed = total_variable = total_total = 0
    for month in months:
        key = _month_key(month)
        total = total_by_month.get(key, 0)
        fixed = fixed_by_month.get(key, 0)
        variable = total - fixed
        fixed_bp = (fixed * 10000) // total if total > 0 else 0
        rows.append(
            {"month": key, "fixed": fixed, "variable": variable, "total": total, "fixed_bp": fixed_bp}
        )
        total_fixed += fixed
        total_variable += variable
        total_total += total
    totals_fixed_bp = (total_fixed * 10000) // total_total if total_total > 0 else 0
    totals = {
        "fixed": total_fixed,
        "variable": total_variable,
        "total": total_total,
        "fixed_bp": totals_fixed_bp,
    }
    return _envelope("fixed-costs", range_param, currency, start_month, end_month, rows, totals)
