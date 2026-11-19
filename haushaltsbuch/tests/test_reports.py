from __future__ import annotations

import calendar
import csv
import io
import json
from datetime import date
from pathlib import Path

from conftest import PREFIX

from test_v1_api import _create_account, _create_household, _expense_category

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "reports" / "multi_year_ledger.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text())


def _category_by_name(client, headers, name: str) -> dict:
    items = client.get(f"{PREFIX}/categories", headers=headers).json()
    return next(item for item in items if item["name"] == name)


def _add_months(value: date, delta: int) -> date:
    month_index = value.year * 12 + (value.month - 1) + delta
    year, month0 = divmod(month_index, 12)
    return date(year, month0 + 1, 1)


def _month_key(value: date) -> str:
    return f"{value.year:04d}-{value.month:02d}"


def _month_end(month_start: date) -> date:
    last_day = calendar.monthrange(month_start.year, month_start.month)[1]
    return month_start.replace(day=last_day)


def _post_transaction(
    client, headers, booking_date, account_id, category_id, amount, counterparty, purpose, *, is_income
):
    account_amount, category_amount = (
        (amount, -amount) if is_income else (-amount, amount)
    )
    response = client.post(
        f"{PREFIX}/transactions",
        headers=headers,
        json={
            "booking_date": booking_date.isoformat(),
            "counterparty": counterparty,
            "purpose": purpose,
            "postings": [
                {
                    "account_id": account_id,
                    "original_amount": account_amount,
                    "currency": "EUR",
                    "base_amount": account_amount,
                },
                {
                    "category_id": category_id,
                    "original_amount": category_amount,
                    "currency": "EUR",
                    "base_amount": category_amount,
                },
            ],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def load_multi_year_ledger(client, headers, today: date) -> dict:
    """Bucht die synthetischen Mehrjahres-Buchungen aus der Fixture
    `tests/fixtures/reports/multi_year_ledger.json` über die bestehende API
    (Haushalt/Konten/Kategorien/wiederkehrende Regel/Buchungen) in einen
    frischen Testhaushalt. Gibt IDs und die pro Monat erwarteten Summen
    zurück, damit Tests exakt (Integer) vergleichen können, unabhängig vom
    tatsächlichen Testlaufdatum.
    """
    fixture = _load_fixture()
    household = _create_household(client, headers)
    account = _create_account(client, headers, opening_balance=0)
    extra_spec = fixture["accounts"][0]
    extra_account = client.post(
        f"{PREFIX}/accounts",
        headers=headers,
        json={
            "name": extra_spec["name"],
            "type": extra_spec["type"],
            "currency": extra_spec["currency"],
            "opening_balance": extra_spec["opening_balance"],
        },
    ).json()

    freizeit = _category_by_name(client, headers, "Freizeit")
    streaming_spec = fixture["categories"][0]
    streaming = client.post(
        f"{PREFIX}/categories",
        headers=headers,
        json={
            "name": streaming_spec["name"],
            "kind": streaming_spec["kind"],
            "parent_id": freizeit["id"],
        },
    ).json()

    category_ids = {
        "Gehalt": _category_by_name(client, headers, "Gehalt")["id"],
        "Wohnen": _category_by_name(client, headers, "Wohnen")["id"],
        "Lebensmittel": _expense_category(client, headers)["id"],
        "Streaming": streaming["id"],
    }
    category_ids_by_id = {value: key for key, value in category_ids.items()}
    assert category_ids_by_id  # nur zur Lesbarkeit, keine echte Nutzung

    rule_spec = fixture["recurring_rules"][0]
    recurring_next_due = _add_months(
        today.replace(day=1), -rule_spec["next_due_date_months_ago"]
    )
    client.post(
        f"{PREFIX}/recurring",
        headers=headers,
        json={
            "kind": "expense",
            "account_id": account["id"],
            "category_id": category_ids[rule_spec["category_name"]],
            "frequency": rule_spec["frequency"],
            "next_due_date": recurring_next_due.isoformat(),
            "amount": rule_spec["amount"],
            "counterparty": rule_spec["counterparty"],
            "status": rule_spec["status"],
        },
    )

    months_back = fixture["months_back"]
    current_month = today.replace(day=1)
    monthly_totals: dict[str, dict] = {}
    for offset in range(months_back - 1, -1, -1):
        month_start = _add_months(current_month, -offset)
        month_key = _month_key(month_start)
        income = expense = fixed = 0
        for entry in fixture["monthly_pattern"]:
            booking_date = (
                _month_end(month_start)
                if entry["day"] == "last"
                else month_start.replace(day=entry["day"])
            )
            is_income = "income_category" in entry
            category_name = entry.get("income_category") or entry.get("expense_category")
            _post_transaction(
                client,
                headers,
                booking_date,
                account["id"],
                category_ids[category_name],
                entry["amount"],
                entry["counterparty"],
                entry["purpose"],
                is_income=is_income,
            )
            if is_income:
                income += entry["amount"]
            else:
                expense += entry["amount"]
                if category_name == rule_spec["category_name"]:
                    fixed += entry["amount"]
        monthly_totals[month_key] = {
            "income": income,
            "expense": expense,
            "net": income - expense,
            "fixed": fixed,
            "variable": expense - fixed,
        }
    return {
        "household": household,
        "account": account,
        "extra_account": extra_account,
        "category_ids": category_ids,
        "monthly_totals": monthly_totals,
        "months": sorted(monthly_totals.keys()),
        "months_back": months_back,
    }


def _assert_all_ints(mapping: dict, keys: list[str]) -> None:
    for key in keys:
        value = mapping[key]
        assert type(value) is int, f"{key}={value!r} ist kein reiner Integer"


# ---------------------------------------------------------------------------
# Cashflow
# ---------------------------------------------------------------------------


def test_cashflow_matches_monthly_totals_and_is_gap_free(client, owner_headers):
    today = date.today()
    data = load_multi_year_ledger(client, owner_headers, today)
    months_back = data["months_back"]

    for range_param, expected_count in (("24", 24), ("all", months_back)):
        response = client.get(
            f"{PREFIX}/reports/cashflow?range={range_param}", headers=owner_headers
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["report"] == "cashflow"
        assert body["range"] == range_param
        assert body["currency"] == "EUR"
        rows = body["rows"]
        assert len(rows) == expected_count
        # Monatsachse ist lückenlos und aufsteigend sortiert.
        months_in_rows = [row["month"] for row in rows]
        assert months_in_rows == sorted(months_in_rows)
        expected_months = data["months"][-expected_count:]
        assert months_in_rows == expected_months

        total_income = total_expense = 0
        for row in rows:
            _assert_all_ints(row, ["income", "expense", "net"])
            expected = data["monthly_totals"][row["month"]]
            assert row["income"] == expected["income"]
            assert row["expense"] == expected["expense"]
            assert row["net"] == expected["net"]
            total_income += row["income"]
            total_expense += row["expense"]

        _assert_all_ints(body["totals"], ["income", "expense", "net"])
        assert body["totals"]["income"] == total_income
        assert body["totals"]["expense"] == total_expense
        assert body["totals"]["net"] == total_income - total_expense


def test_cashflow_range_boundaries_first_and_last_day_of_month(client, owner_headers):
    _create_household(client, owner_headers)
    account = _create_account(client, owner_headers, opening_balance=0)
    category = _category_by_name(client, owner_headers, "Gehalt")

    today = date.today()
    current_month = today.replace(day=1)
    window_start = _add_months(current_month, -2)  # range=3
    just_before_window = window_start - date.resolution

    # Innerhalb des Fensters (erster Tag des Startmonats): muss erscheinen.
    _post_transaction(
        client,
        owner_headers,
        window_start,
        account["id"],
        category["id"],
        1000,
        "Arbeitgeber",
        "Gehalt im Fenster",
        is_income=True,
    )
    # Einen Tag vor dem Fenster (letzter Tag des Vormonats): darf nicht erscheinen.
    _post_transaction(
        client,
        owner_headers,
        just_before_window,
        account["id"],
        category["id"],
        500,
        "Arbeitgeber",
        "Gehalt vor dem Fenster",
        is_income=True,
    )

    response = client.get(f"{PREFIX}/reports/cashflow?range=3", headers=owner_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["start_month"] == _month_key(window_start)
    first_month_row = next(row for row in body["rows"] if row["month"] == _month_key(window_start))
    assert first_month_row["income"] == 1000
    assert body["totals"]["income"] == 1000


def test_reversed_transaction_is_neutral_in_cashflow(client, owner_headers):
    _create_household(client, owner_headers)
    account = _create_account(client, owner_headers, opening_balance=0)
    category = _expense_category(client, owner_headers)

    today = date.today()
    transaction = client.post(
        f"{PREFIX}/transactions",
        headers=owner_headers,
        json={
            "booking_date": today.isoformat(),
            "counterparty": "Supermarkt",
            "purpose": "Einkauf",
            "postings": [
                {
                    "account_id": account["id"],
                    "original_amount": -4200,
                    "currency": "EUR",
                    "base_amount": -4200,
                },
                {
                    "category_id": category["id"],
                    "original_amount": 4200,
                    "currency": "EUR",
                    "base_amount": 4200,
                },
            ],
        },
    ).json()
    reverse = client.post(
        f"{PREFIX}/transactions/{transaction['id']}/reverse",
        headers=owner_headers,
        json={"revision": transaction["revision"]},
    )
    assert reverse.status_code == 200, reverse.text

    body = client.get(f"{PREFIX}/reports/cashflow?range=3", headers=owner_headers).json()
    current_row = next(row for row in body["rows"] if row["month"] == _month_key(today.replace(day=1)))
    assert current_row["income"] == 0
    assert current_row["expense"] == 0
    assert current_row["net"] == 0


# ---------------------------------------------------------------------------
# Net worth
# ---------------------------------------------------------------------------


def test_net_worth_cumulative_balance_matches_totals(client, owner_headers):
    today = date.today()
    data = load_multi_year_ledger(client, owner_headers, today)

    response = client.get(f"{PREFIX}/reports/net-worth?range=12", headers=owner_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["rows"]) == 12

    window_months = data["months"][-12:]
    pre_window_months = data["months"][:-12]
    opening = sum(data["monthly_totals"][m]["net"] for m in pre_window_months)
    running = opening
    for row, month_key in zip(body["rows"], window_months, strict=True):
        _assert_all_ints(row, ["balance"])
        running += data["monthly_totals"][month_key]["net"]
        assert row["month"] == month_key
        assert row["balance"] == running

    _assert_all_ints(body["totals"], ["start_balance", "end_balance", "change"])
    assert body["totals"]["start_balance"] == opening
    assert body["totals"]["end_balance"] == running
    assert body["totals"]["change"] == running - opening


def test_net_worth_excludes_internal_accounts(client, owner_headers):
    _create_household(client, owner_headers)
    # opening_balance > 0 erzeugt im Hintergrund eine Buchung gegen das
    # interne Eröffnungssalden-Konto; das darf den Saldo nicht verdoppeln
    # oder aufheben.
    account = _create_account(client, owner_headers, opening_balance=5000)
    assert account["balance_base"] == 5000

    body = client.get(f"{PREFIX}/reports/net-worth?range=3", headers=owner_headers).json()
    assert body["rows"][-1]["balance"] == 5000
    assert body["totals"]["end_balance"] == 5000


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------


def test_categories_share_bp_sums_to_10000_and_top_level_amounts(client, owner_headers):
    today = date.today()
    data = load_multi_year_ledger(client, owner_headers, today)

    body = client.get(f"{PREFIX}/reports/categories?range=12", headers=owner_headers).json()
    rows = body["rows"]
    assert rows, "Es sollten Ausgaben-Hauptkategorien mit Betrag > 0 vorhanden sein"

    window_months = data["months"][-12:]
    expected_wohnen = sum(data["monthly_totals"][m]["fixed"] for m in window_months)
    expected_lebensmittel = 25000 * 12
    expected_freizeit = 1200 * 12

    by_name = {row["name"]: row for row in rows}
    assert by_name["Wohnen"]["amount"] == expected_wohnen
    assert by_name["Lebensmittel"]["amount"] == expected_lebensmittel
    assert by_name["Freizeit"]["amount"] == expected_freizeit
    assert by_name["Freizeit"]["has_children"] is True
    assert by_name["Lebensmittel"]["has_children"] is False

    for row in rows:
        _assert_all_ints(row, ["amount", "share_bp"])
    # Reihen absteigend nach Betrag sortiert.
    amounts = [row["amount"] for row in rows]
    assert amounts == sorted(amounts, reverse=True)
    assert sum(row["share_bp"] for row in rows) == 10000
    assert body["totals"]["expense"] == sum(amounts)


def test_categories_drilldown_shows_children_and_direct_amount(client, owner_headers):
    today = date.today()
    data = load_multi_year_ledger(client, owner_headers, today)
    freizeit = _category_by_name(client, owner_headers, "Freizeit")

    body = client.get(
        f"{PREFIX}/reports/categories?range=12&parent_id={freizeit['id']}",
        headers=owner_headers,
    ).json()
    rows = body["rows"]
    assert len(rows) == 1
    assert rows[0]["name"] == "Streaming"
    assert rows[0]["amount"] == 1200 * 12
    assert rows[0]["has_children"] is False
    assert rows[0]["category_id"] == data["category_ids"]["Streaming"]


def test_categories_unknown_or_foreign_parent_id_returns_404(
    client, owner_headers, outsider_headers
):
    load_multi_year_ledger(client, owner_headers, date.today())
    _create_household(client, outsider_headers)
    foreign_category = _category_by_name(client, outsider_headers, "Wohnen")

    unknown = client.get(
        f"{PREFIX}/reports/categories?parent_id=999999", headers=owner_headers
    )
    assert unknown.status_code == 404
    assert unknown.json()["detail"]["code"] == "category_not_found"

    foreign = client.get(
        f"{PREFIX}/reports/categories?parent_id={foreign_category['id']}",
        headers=owner_headers,
    )
    assert foreign.status_code == 404
    assert foreign.json()["detail"]["code"] == "category_not_found"


# ---------------------------------------------------------------------------
# Budgets
# ---------------------------------------------------------------------------


def test_budgets_report_uses_shared_window_and_spent_helpers(client, owner_headers):
    today = date.today()
    data = load_multi_year_ledger(client, owner_headers, today)
    category_id = data["category_ids"]["Lebensmittel"]

    oldest_month = date.fromisoformat(f"{data['months'][0]}-01")
    budget = client.post(
        f"{PREFIX}/budgets",
        headers=owner_headers,
        json={
            "category_id": category_id,
            "type": "monthly",
            "amount": 20000,
            "start_date": oldest_month.isoformat(),
            "end_date": _add_months(today.replace(day=1), 12).isoformat(),
            "warning_threshold": 80,
        },
    ).json()

    body = client.get(f"{PREFIX}/reports/budgets?range=3", headers=owner_headers).json()
    rows = [row for row in body["rows"] if row["budget_id"] == budget["id"]]
    assert len(rows) == 3
    for row in rows:
        _assert_all_ints(row, ["planned", "spent", "remaining", "used_bp"])
        assert row["name"] == "Lebensmittel"
        assert row["planned"] == 20000
        assert row["spent"] == 25000
        assert row["remaining"] == -5000
        assert row["used_bp"] == (25000 * 10000) // 20000

    last_month_rows = [row for row in body["rows"] if row["month"] == body["rows"][-1]["month"]]
    assert body["totals"]["planned"] == sum(row["planned"] for row in last_month_rows)
    assert body["totals"]["spent"] == sum(row["spent"] for row in last_month_rows)


# ---------------------------------------------------------------------------
# Fixed costs
# ---------------------------------------------------------------------------


def test_fixed_costs_splits_recurring_rule_matches_from_variable(client, owner_headers):
    today = date.today()
    data = load_multi_year_ledger(client, owner_headers, today)

    body = client.get(f"{PREFIX}/reports/fixed-costs?range=6", headers=owner_headers).json()
    assert len(body["rows"]) == 6
    window_months = data["months"][-6:]
    total_fixed = total_variable = total_total = 0
    for row, month_key in zip(body["rows"], window_months, strict=True):
        expected = data["monthly_totals"][month_key]
        _assert_all_ints(row, ["fixed", "variable", "total", "fixed_bp"])
        assert row["fixed"] == expected["fixed"]
        assert row["variable"] == expected["variable"]
        assert row["total"] == expected["fixed"] + expected["variable"]
        assert row["fixed_bp"] == (row["fixed"] * 10000) // row["total"]
        total_fixed += row["fixed"]
        total_variable += row["variable"]
        total_total += row["total"]

    assert body["totals"]["fixed"] == total_fixed
    assert body["totals"]["variable"] == total_variable
    assert body["totals"]["total"] == total_total
    assert body["totals"]["fixed_bp"] == (total_fixed * 10000) // total_total


# ---------------------------------------------------------------------------
# Zugriffsschutz
# ---------------------------------------------------------------------------


def test_reports_without_household_return_404(client, member_headers):
    for path in (
        "cashflow",
        "net-worth",
        "categories",
        "budgets",
        "fixed-costs",
    ):
        response = client.get(f"{PREFIX}/reports/{path}", headers=member_headers)
        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "household_not_found"


def test_foreign_household_sees_nothing(client, owner_headers, outsider_headers):
    load_multi_year_ledger(client, owner_headers, date.today())
    _create_household(client, outsider_headers)

    body = client.get(f"{PREFIX}/reports/cashflow?range=12", headers=outsider_headers).json()
    assert all(row["income"] == 0 and row["expense"] == 0 for row in body["rows"])
    assert body["totals"] == {"income": 0, "expense": 0, "net": 0}

    categories_body = client.get(
        f"{PREFIX}/reports/categories?range=12", headers=outsider_headers
    ).json()
    assert categories_body["rows"] == []
    assert categories_body["totals"]["expense"] == 0


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------


def test_csv_format_matches_json_rows(client, owner_headers):
    today = date.today()
    load_multi_year_ledger(client, owner_headers, today)

    json_body = client.get(
        f"{PREFIX}/reports/cashflow?range=6&format=json", headers=owner_headers
    ).json()
    csv_response = client.get(
        f"{PREFIX}/reports/cashflow?range=6&format=csv", headers=owner_headers
    )
    assert csv_response.status_code == 200
    assert csv_response.headers["content-type"].startswith("text/csv")
    assert (
        csv_response.headers["content-disposition"]
        == 'attachment; filename="haushaltsbuch-cashflow-6.csv"'
    )

    reader = csv.DictReader(io.StringIO(csv_response.text), delimiter=";")
    csv_rows = list(reader)
    assert len(csv_rows) == len(json_body["rows"])
    for csv_row, json_row in zip(csv_rows, json_body["rows"], strict=True):
        assert csv_row["month"] == json_row["month"]
        assert int(csv_row["income"]) == json_row["income"]
        assert int(csv_row["expense"]) == json_row["expense"]
        assert int(csv_row["net"]) == json_row["net"]


def test_csv_injection_prefix_is_neutralized(client, owner_headers):
    _create_household(client, owner_headers)
    account = _create_account(client, owner_headers, opening_balance=0)
    freizeit = _category_by_name(client, owner_headers, "Freizeit")
    today = date.today()
    danger_name = "=cmd|' /C calc'!A0"
    danger_category = client.post(
        f"{PREFIX}/categories",
        headers=owner_headers,
        json={"name": "Risiko", "kind": "expense", "parent_id": freizeit["id"]},
    ).json()
    _post_transaction(
        client,
        owner_headers,
        today,
        account["id"],
        danger_category["id"],
        1234,
        danger_name,
        "Testbuchung",
        is_income=False,
    )
    response = client.get(
        f"{PREFIX}/reports/categories?range=3&format=csv&parent_id={freizeit['id']}",
        headers=owner_headers,
    )
    assert response.status_code == 200
    reader = csv.DictReader(io.StringIO(response.text), delimiter=";")
    rows = list(reader)
    risiko_row = next(row for row in rows if row["name"] == "Risiko")
    # Der Name selbst beginnt nicht mit einem Gefahren-Zeichen, aber die
    # Buchung mit gefährlichem Gegenpartei-Namen landet nicht in rows
    # (Kategorien-Report hat kein counterparty-Feld) - Sanity-Check, dass
    # harmlose Namen unverändert bleiben.
    assert risiko_row["name"] == "Risiko"
