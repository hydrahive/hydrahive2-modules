from __future__ import annotations

import json

from conftest import PREFIX
from test_v1_api import _create_account, _create_household, _expense_category

_CSV_MAPPING = {
    "booking_date": "Datum",
    "amount": "Betrag",
    "counterparty": "Empfaenger",
    "purpose": "Zweck",
    "delimiter": ";",
    "encoding": "utf-8",
    "decimal_separator": ",",
    "date_format": "%d.%m.%Y",
}


def _upload_csv(client, headers, account_id, payload: bytes, *, filename="k.csv"):
    return client.post(
        f"{PREFIX}/imports",
        headers=headers,
        data={"account_id": str(account_id), "format": "csv", "mapping": json.dumps(_CSV_MAPPING)},
        files={"file": (filename, payload, "text/csv")},
    )


def _income_category(client, headers) -> dict:
    response = client.get(f"{PREFIX}/categories", headers=headers)
    assert response.status_code == 200
    return next(item for item in response.json() if item["name"] == "Gehalt")


def _new_row_has_no_suggestion(client, owner_headers):
    _create_household(client, owner_headers)
    account = _create_account(client, owner_headers, opening_balance=0)
    payload = "Datum;Betrag;Empfaenger;Zweck\n02.01.2025;-12,34;REWE;Einkauf".encode()
    batch = _upload_csv(client, owner_headers, account["id"], payload).json()
    return account, batch


def test_upload_row_has_null_suggestion_fields(client, owner_headers):
    _account, batch = _new_row_has_no_suggestion(client, owner_headers)
    row = batch["rows"][0]
    assert row["suggested_category_id"] is None
    assert row["suggestion_source"] is None
    assert row["suggestion_confidence"] is None


def _book_history(client, owner_headers, account, category, *, counterparty, amount):
    """Bucht eine Transaktion, damit die Historie einen Händler kennt."""
    body = {
        "booking_date": "2025-01-05",
        "counterparty": counterparty,
        "source": "manual",
        "postings": [
            {"account_id": account["id"], "original_amount": amount, "currency": "EUR", "base_amount": amount},
            {"category_id": category["id"], "original_amount": -amount, "currency": "EUR", "base_amount": -amount},
        ],
    }
    response = client.post(f"{PREFIX}/transactions", headers=owner_headers, json=body)
    assert response.status_code == 201, response.text
    return response.json()


def test_history_suggestion_without_llm(client, owner_headers, monkeypatch):
    _create_household(client, owner_headers)
    account = _create_account(client, owner_headers, opening_balance=100_000)
    category = _expense_category(client, owner_headers)
    _book_history(client, owner_headers, account, category, counterparty="REWE", amount=-500)

    # LLM darf gar nicht angefragt werden, wenn Historie greift.
    async def _boom(*_args, **_kwargs):
        raise AssertionError("LLM should not be called when history matches")

    monkeypatch.setattr("backend.categorize_llm.complete", _boom)

    payload = "Datum;Betrag;Empfaenger;Zweck\n10.02.2025;-19,99;REWE;Wocheneinkauf".encode()
    batch = _upload_csv(client, owner_headers, account["id"], payload).json()

    suggested = client.post(
        f"{PREFIX}/imports/{batch['id']}/suggest-categories",
        headers=owner_headers,
        json={},
    )
    assert suggested.status_code == 200, suggested.text
    row = suggested.json()["rows"][0]
    assert row["suggested_category_id"] == category["id"]
    assert row["suggestion_source"] == "history"
    assert row["suggestion_confidence"] >= 0.6


def test_llm_suggestion_dedupes_and_applies(client, owner_headers, monkeypatch):
    _create_household(client, owner_headers)
    account = _create_account(client, owner_headers, opening_balance=0)
    category = _expense_category(client, owner_headers)

    calls: list = []

    async def _fake_complete(messages, *, model=None, temperature=0.0, max_tokens=2048):
        calls.append(messages)
        prompt = messages[-1]["content"]
        # Für jeden merchant_key im Prompt die Lebensmittel-Kategorie vorschlagen.
        keys = [line.split(" :: ")[0] for line in prompt.splitlines() if " :: " in line]
        return json.dumps([
            {"merchant_key": key, "category_id": category["id"], "confidence": 0.8}
            for key in keys
        ])

    monkeypatch.setattr("backend.categorize_llm.complete", _fake_complete)

    payload = (
        "Datum;Betrag;Empfaenger;Zweck\n"
        "01.03.2025;-10,00;ALDI;Einkauf\n"
        "05.03.2025;-20,00;ALDI;Einkauf\n"
        "07.03.2025;-30,00;ALDI;Einkauf"
    ).encode()
    batch = _upload_csv(client, owner_headers, account["id"], payload).json()

    suggested = client.post(
        f"{PREFIX}/imports/{batch['id']}/suggest-categories",
        headers=owner_headers,
        json={"model": "openai/gpt-4o-mini"},
    ).json()

    # Drei Zeilen, ein Händler → genau ein LLM-Call.
    assert len(calls) == 1
    assert all(row["suggested_category_id"] == category["id"] for row in suggested["rows"])
    assert all(row["suggestion_source"] == "llm" for row in suggested["rows"])


def test_accept_suggestions_then_complete(client, owner_headers, monkeypatch):
    _create_household(client, owner_headers)
    account = _create_account(client, owner_headers, opening_balance=0)
    category = _expense_category(client, owner_headers)

    async def _fake_complete(messages, *, model=None, temperature=0.0, max_tokens=2048):
        prompt = messages[-1]["content"]
        keys = [line.split(" :: ")[0] for line in prompt.splitlines() if " :: " in line]
        return json.dumps([
            {"merchant_key": key, "category_id": category["id"], "confidence": 0.9}
            for key in keys
        ])

    monkeypatch.setattr("backend.categorize_llm.complete", _fake_complete)

    payload = "Datum;Betrag;Empfaenger;Zweck\n01.04.2025;-42,00;LIDL;Einkauf".encode()
    batch = _upload_csv(client, owner_headers, account["id"], payload).json()
    batch = client.post(
        f"{PREFIX}/imports/{batch['id']}/suggest-categories",
        headers=owner_headers,
        json={},
    ).json()

    accepted = client.post(
        f"{PREFIX}/imports/{batch['id']}/accept-suggestions",
        headers=owner_headers,
        json={"revision": batch["revision"]},
    )
    assert accepted.status_code == 200, accepted.text
    row = accepted.json()["rows"][0]
    assert row["status"] == "accepted"
    assert row["category_id"] == category["id"]

    completed = client.post(
        f"{PREFIX}/imports/{batch['id']}/complete",
        headers=owner_headers,
        json={"revision": accepted.json()["revision"]},
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "imported"

    transactions = client.get(f"{PREFIX}/transactions", headers=owner_headers).json()
    assert len(transactions) == 1


def test_suggest_rejects_non_draft_and_foreign_household(client, owner_headers, outsider_headers, monkeypatch):
    _create_household(client, owner_headers)
    account = _create_account(client, owner_headers, opening_balance=0)

    async def _noop(*_args, **_kwargs):
        return "[]"

    monkeypatch.setattr("backend.categorize_llm.complete", _noop)

    payload = "Datum;Betrag;Empfaenger;Zweck\n01.05.2025;-5,00;KIOSK;Snack".encode()
    batch = _upload_csv(client, owner_headers, account["id"], payload).json()

    hidden = client.post(
        f"{PREFIX}/imports/{batch['id']}/suggest-categories",
        headers=outsider_headers,
        json={},
    )
    assert hidden.status_code == 404

    category = _expense_category(client, owner_headers)
    row = batch["rows"][0]
    client.patch(
        f"{PREFIX}/imports/{batch['id']}/rows/{row['id']}",
        headers=owner_headers,
        json={"revision": row["revision"], "status": "accepted", "category_id": category["id"]},
    )
    completed = client.post(
        f"{PREFIX}/imports/{batch['id']}/complete",
        headers=owner_headers,
        json={"revision": batch["revision"]},
    ).json()

    conflict = client.post(
        f"{PREFIX}/imports/{batch['id']}/suggest-categories",
        headers=owner_headers,
        json={},
    )
    assert conflict.status_code == 409
    assert completed["status"] == "imported"
