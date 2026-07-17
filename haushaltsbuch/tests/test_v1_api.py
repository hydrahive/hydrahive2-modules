from __future__ import annotations

from datetime import date, timedelta

from conftest import PREFIX


def _create_household(client, headers, *, name="Testhaushalt") -> dict:
    response = client.post(
        f"{PREFIX}/household",
        headers=headers,
        json={"name": name, "base_currency": "EUR", "timezone": "Europe/Berlin"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_account(client, headers, *, opening_balance=10_000) -> dict:
    response = client.post(
        f"{PREFIX}/accounts",
        headers=headers,
        json={
            "name": "Girokonto",
            "type": "checking",
            "currency": "EUR",
            "opening_balance": opening_balance,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _expense_category(client, headers) -> dict:
    response = client.get(f"{PREFIX}/categories", headers=headers)
    assert response.status_code == 200
    return next(item for item in response.json() if item["name"] == "Lebensmittel")


def test_auth_and_household_isolation(client, owner_headers, outsider_headers):
    assert client.get(f"{PREFIX}/household").status_code == 401
    _create_household(client, owner_headers)

    hidden = client.get(f"{PREFIX}/household", headers=outsider_headers)
    assert hidden.status_code == 404
    assert hidden.json()["detail"]["code"] == "household_not_found"


def test_owner_can_add_exact_existing_user(client, owner_headers, member_headers):
    _create_household(client, owner_headers)

    added = client.post(
        f"{PREFIX}/household/members",
        headers=owner_headers,
        json={"username": "member"},
    )
    assert added.status_code == 201, added.text
    assert added.json()["user_id"] == "user-member"

    shared = client.get(f"{PREFIX}/household", headers=member_headers)
    assert shared.status_code == 200
    assert shared.json()["current_role"] == "member"

    owned_account = client.post(
        f"{PREFIX}/accounts",
        headers=owner_headers,
        json={
            "name": "Mitgliedskonto",
            "type": "checking",
            "owner_member_id": added.json()["id"],
            "currency": "EUR",
            "opening_balance": 0,
        },
    )
    assert owned_account.status_code == 201
    removed = client.delete(
        f"{PREFIX}/household/members/{added.json()['id']}?revision={added.json()['revision']}",
        headers=owner_headers,
    )
    assert removed.status_code == 204
    account_after = client.get(f"{PREFIX}/accounts", headers=owner_headers).json()[0]
    assert account_after["owner_member_id"] is None

    missing = client.post(
        f"{PREFIX}/household/members",
        headers=owner_headers,
        json={"username": "does-not-exist"},
    )
    assert missing.status_code == 404


def test_invite_is_hashed_one_time_and_owner_only(
    client,
    owner_headers,
    member_headers,
    outsider_headers,
):
    _create_household(client, owner_headers)
    client.post(
        f"{PREFIX}/household/members",
        headers=owner_headers,
        json={"username": "member"},
    )
    assert (
        client.post(
            f"{PREFIX}/household/invites",
            headers=member_headers,
            json={"expires_in_hours": 24},
        ).status_code
        == 403
    )

    created = client.post(
        f"{PREFIX}/household/invites",
        headers=owner_headers,
        json={"expires_in_hours": 24},
    )
    assert created.status_code == 201, created.text
    code = created.json()["code"]
    assert "token_hash" not in created.json()

    accepted = client.post(
        f"{PREFIX}/household/invites/accept",
        headers=outsider_headers,
        json={"code": code},
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["user_id"] == "user-outsider"

    reused = client.post(
        f"{PREFIX}/household/invites/accept",
        headers=outsider_headers,
        json={"code": code},
    )
    assert reused.status_code == 409


def test_balanced_ledger_balance_reversal_and_audit(client, owner_headers):
    _create_household(client, owner_headers)
    account = _create_account(client, owner_headers)
    category = _expense_category(client, owner_headers)

    transaction = client.post(
        f"{PREFIX}/transactions",
        headers=owner_headers,
        json={
            "booking_date": date.today().isoformat(),
            "counterparty": "Supermarkt",
            "purpose": "Einkauf",
            "postings": [
                {
                    "account_id": account["id"],
                    "original_amount": -2500,
                    "currency": "EUR",
                    "base_amount": -2500,
                },
                {
                    "category_id": category["id"],
                    "original_amount": 2500,
                    "currency": "EUR",
                    "base_amount": 2500,
                },
            ],
        },
    )
    assert transaction.status_code == 201, transaction.text
    assert sum(p["base_amount"] for p in transaction.json()["postings"]) == 0

    accounts = client.get(f"{PREFIX}/accounts", headers=owner_headers).json()
    assert (
        next(item for item in accounts if item["id"] == account["id"])["balance_base"]
        == 7500
    )

    account_update = {
        "name": account["name"],
        "type": account["type"],
        "owner_member_id": account["owner_member_id"],
        "bank_identifier": account["bank_identifier"],
        "archived": True,
        "revision": account["revision"],
    }
    assert (
        client.put(
            f"{PREFIX}/accounts/{account['id']}",
            headers=owner_headers,
            json=account_update,
        ).status_code
        == 200
    )
    category_update = {
        "name": category["name"],
        "kind": category["kind"],
        "parent_id": category["parent_id"],
        "icon": category["icon"],
        "color": category["color"],
        "sort_order": category["sort_order"],
        "archived": True,
        "revision": category["revision"],
    }
    assert (
        client.put(
            f"{PREFIX}/categories/{category['id']}",
            headers=owner_headers,
            json=category_update,
        ).status_code
        == 200
    )

    reversed_tx = client.post(
        f"{PREFIX}/transactions/{transaction.json()['id']}/reverse",
        headers=owner_headers,
        json={"revision": transaction.json()["revision"]},
    )
    assert reversed_tx.status_code == 200, reversed_tx.text
    accounts = client.get(
        f"{PREFIX}/accounts?include_archived=true",
        headers=owner_headers,
    ).json()
    assert (
        next(item for item in accounts if item["id"] == account["id"])["balance_base"]
        == 10000
    )
    dashboard = client.get(f"{PREFIX}/dashboard", headers=owner_headers).json()
    assert dashboard["month_expense"] == 0

    duplicate = client.post(
        f"{PREFIX}/transactions/{transaction.json()['id']}/reverse",
        headers=owner_headers,
        json={"revision": transaction.json()["revision"]},
    )
    assert duplicate.status_code == 409
    assert len(client.get(f"{PREFIX}/audit", headers=owner_headers).json()) >= 4


def test_unbalanced_transaction_is_rejected_atomically(client, owner_headers):
    _create_household(client, owner_headers)
    account = _create_account(client, owner_headers, opening_balance=0)
    category = _expense_category(client, owner_headers)

    response = client.post(
        f"{PREFIX}/transactions",
        headers=owner_headers,
        json={
            "booking_date": date.today().isoformat(),
            "postings": [
                {
                    "account_id": account["id"],
                    "original_amount": -100,
                    "currency": "EUR",
                    "base_amount": -100,
                },
                {
                    "category_id": category["id"],
                    "original_amount": 90,
                    "currency": "EUR",
                    "base_amount": 90,
                },
            ],
        },
    )
    assert response.status_code == 422
    assert client.get(f"{PREFIX}/transactions", headers=owner_headers).json() == []


def test_revision_conflict_and_budget_overlap(client, owner_headers):
    _create_household(client, owner_headers)
    account = _create_account(client, owner_headers, opening_balance=0)
    update = {
        "name": "Girokonto neu",
        "type": "checking",
        "archived": False,
        "revision": account["revision"],
    }
    assert (
        client.put(
            f"{PREFIX}/accounts/{account['id']}",
            headers=owner_headers,
            json=update,
        ).status_code
        == 200
    )
    assert (
        client.put(
            f"{PREFIX}/accounts/{account['id']}",
            headers=owner_headers,
            json=update,
        ).status_code
        == 409
    )

    category = _expense_category(client, owner_headers)
    start = date.today().replace(day=1)
    end = start + timedelta(days=60)
    budget = {
        "category_id": category["id"],
        "type": "monthly",
        "amount": 40_000,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "warning_threshold": 80,
    }
    assert (
        client.post(f"{PREFIX}/budgets", headers=owner_headers, json=budget).status_code
        == 201
    )
    assert (
        client.post(f"{PREFIX}/budgets", headers=owner_headers, json=budget).status_code
        == 409
    )


def test_monthly_rollover_includes_retroactive_adjustments(client, owner_headers):
    _create_household(client, owner_headers)
    account = _create_account(client, owner_headers, opening_balance=20_000)
    category = _expense_category(client, owner_headers)
    budget = client.post(
        f"{PREFIX}/budgets",
        headers=owner_headers,
        json={
            "category_id": category["id"],
            "type": "monthly_rollover",
            "amount": 10_000,
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "warning_threshold": 80,
        },
    ).json()
    closed = client.post(
        f"{PREFIX}/budgets/{budget['id']}/close",
        headers=owner_headers,
        json={"start_date": "2026-01-01", "end_date": "2026-01-31", "revision": 1},
    )
    assert closed.status_code == 200, closed.text
    assert closed.json()["rollover_amount"] == 10_000
    transaction = {
        "booking_date": "2026-01-15",
        "postings": [
            {
                "account_id": account["id"],
                "original_amount": -2000,
                "currency": "EUR",
                "base_amount": -2000,
            },
            {
                "category_id": category["id"],
                "original_amount": 2000,
                "currency": "EUR",
                "base_amount": 2000,
            },
        ],
    }
    assert (
        client.post(
            f"{PREFIX}/transactions",
            headers=owner_headers,
            json=transaction,
        ).status_code
        == 201
    )
    closed_february = client.post(
        f"{PREFIX}/budgets/{budget['id']}/close",
        headers=owner_headers,
        json={"start_date": "2026-02-01", "end_date": "2026-02-28", "revision": 2},
    )
    assert closed_february.status_code == 200, closed_february.text
    assert closed_february.json()["base_allocation_amount"] == 10_000
    assert closed_february.json()["allocated_amount"] == 18_000
    assert closed_february.json()["rollover_amount"] == 18_000

    listed = client.get(
        f"{PREFIX}/budgets?on_date=2026-03-15",
        headers=owner_headers,
    ).json()[0]
    assert listed["available_amount"] == 28_000
    assert listed["periods"][0]["adjustment_amount"] == 2000
    assert listed["periods"][0]["effective_rollover_amount"] == 8000
    assert listed["periods"][1]["effective_allocated_amount"] == 18_000
    assert listed["periods"][1]["effective_rollover_amount"] == 18_000

    updated = client.put(
        f"{PREFIX}/budgets/{budget['id']}",
        headers=owner_headers,
        json={
            "category_id": category["id"],
            "type": "monthly_rollover",
            "amount": 50_000,
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "warning_threshold": 80,
            "active": True,
            "revision": 3,
        },
    )
    assert updated.status_code == 200, updated.text
    after_edit = client.get(
        f"{PREFIX}/budgets?on_date=2026-03-15",
        headers=owner_headers,
    ).json()[0]
    assert after_edit["available_amount"] == 68_000
    assert after_edit["periods"][0]["base_allocation_amount"] == 10_000
    assert after_edit["periods"][1]["base_allocation_amount"] == 10_000
    assert after_edit["periods"][1]["effective_rollover_amount"] == 18_000


def test_base_currency_is_immutable_and_fx_amount_is_validated(client, owner_headers):
    household = _create_household(client, owner_headers)
    changed = client.put(
        f"{PREFIX}/household",
        headers=owner_headers,
        json={
            "name": household["name"],
            "base_currency": "USD",
            "timezone": household["timezone"],
            "revision": household["revision"],
        },
    )
    assert changed.status_code == 409

    account = client.post(
        f"{PREFIX}/accounts",
        headers=owner_headers,
        json={
            "name": "Dollar-Konto",
            "type": "wallet",
            "currency": "USD",
            "opening_balance": 0,
        },
    ).json()
    category = _expense_category(client, owner_headers)
    body = {
        "booking_date": date.today().isoformat(),
        "postings": [
            {
                "account_id": account["id"],
                "original_amount": -1000,
                "currency": "USD",
                "base_amount": -900,
                "exchange_rate": "0.9",
                "exchange_rate_date": date.today().isoformat(),
                "exchange_rate_source": "manual",
            },
            {
                "category_id": category["id"],
                "original_amount": 900,
                "currency": "EUR",
                "base_amount": 900,
            },
        ],
    }
    assert (
        client.post(
            f"{PREFIX}/transactions",
            headers=owner_headers,
            json=body,
        ).status_code
        == 201
    )
    body["postings"][0]["base_amount"] = -899
    body["postings"][1]["original_amount"] = 899
    body["postings"][1]["base_amount"] = 899
    mismatch = client.post(
        f"{PREFIX}/transactions",
        headers=owner_headers,
        json=body,
    )
    assert mismatch.status_code == 422
    assert mismatch.json()["detail"]["code"] == "exchange_rate_amount_mismatch"


def test_monthly_recurring_forecast_keeps_anchor_day(client, owner_headers):
    _create_household(client, owner_headers)
    account = _create_account(client, owner_headers, opening_balance=0)
    category = _expense_category(client, owner_headers)
    created = client.post(
        f"{PREFIX}/recurring",
        headers=owner_headers,
        json={
            "kind": "expense",
            "account_id": account["id"],
            "category_id": category["id"],
            "frequency": "monthly",
            "next_due_date": "2028-01-31",
            "anchor_day": 31,
            "amount": 1000,
            "status": "confirmed",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["anchor_day"] == 31

    # The pure recurrence function makes the clamp invariant deterministic,
    # independent from today's date used by the forecast endpoint.
    from backend.recurring import next_occurrence

    february = next_occurrence(date(2028, 1, 31), "monthly", 1, 31)
    march = next_occurrence(february, "monthly", 1, 31)
    assert february == date(2028, 2, 29)
    assert march == date(2028, 3, 31)
