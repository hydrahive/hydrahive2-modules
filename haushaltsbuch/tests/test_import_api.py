from __future__ import annotations

import json
from pathlib import Path

from conftest import PREFIX
from test_v1_api import _create_account, _create_household, _expense_category

FIXTURES = Path(__file__).parent / "fixtures"


def _upload(client, headers, account_id, fixture="camt-v8.xml", **fields):
    data = (FIXTURES / fixture).read_bytes()
    return client.post(
        f"{PREFIX}/imports",
        headers=headers,
        data={"account_id": str(account_id), "format": fields.pop("format", "camt"), **fields},
        files={"file": ("../private/statement.xml", data, "application/octet-stream")},
    )


def test_upload_creates_draft_without_ledger_mutation_and_masks_bank_data(client, owner_headers):
    _create_household(client, owner_headers)
    account = _create_account(client, owner_headers, opening_balance=0)
    before = client.get(f"{PREFIX}/transactions", headers=owner_headers).json()

    response = _upload(client, owner_headers, account["id"])
    assert response.status_code == 201, response.text
    batch = response.json()
    assert batch["status"] == "draft"
    assert batch["display_filename"] == "statement.xml"
    assert batch["rows"][0]["counterparty_identifier"] == "****3000"
    assert client.get(f"{PREFIX}/transactions", headers=owner_headers).json() == before

    from hydrahive.db.connection import db

    with db() as conn:
        dump = " ".join(str(value) for row in conn.execute("SELECT * FROM module_haushaltsbuch_import_rows") for value in row)
    assert "DE89370400440532013000" not in dump


def test_draft_can_be_deleted_and_same_file_reuploaded(
    client, owner_headers, outsider_headers
):
    _create_household(client, owner_headers)
    account = _create_account(client, owner_headers, opening_balance=0)
    batch = _upload(client, owner_headers, account["id"]).json()

    query = f"revision={batch['revision']}&rows_revision={batch['rows_revision']}"
    hidden = client.delete(
        f"{PREFIX}/imports/{batch['id']}?{query}", headers=outsider_headers
    )
    assert hidden.status_code == 404

    row = batch["rows"][0]
    changed = client.patch(
        f"{PREFIX}/imports/{batch['id']}/rows/{row['id']}",
        headers=owner_headers,
        json={"revision": row["revision"], "status": "rejected"},
    )
    assert changed.status_code == 200
    stale = client.delete(
        f"{PREFIX}/imports/{batch['id']}?{query}", headers=owner_headers
    )
    assert stale.status_code == 409

    refreshed = client.get(
        f"{PREFIX}/imports/{batch['id']}", headers=owner_headers
    ).json()
    deleted = client.delete(
        f"{PREFIX}/imports/{batch['id']}?revision={refreshed['revision']}"
        f"&rows_revision={refreshed['rows_revision']}",
        headers=owner_headers,
    )
    assert deleted.status_code == 204, deleted.text
    assert client.get(
        f"{PREFIX}/imports/{batch['id']}", headers=owner_headers
    ).status_code == 404
    assert client.get(f"{PREFIX}/transactions", headers=owner_headers).json() == []
    audit = client.get(f"{PREFIX}/audit", headers=owner_headers).json()
    assert any(event["action"] == "delete_draft" for event in audit)

    from hydrahive.db.connection import db

    with db() as conn:
        assert conn.execute(
            "SELECT 1 FROM module_haushaltsbuch_import_rows WHERE id=?", (row["id"],)
        ).fetchone() is None

    retried = _upload(client, owner_headers, account["id"])
    assert retried.status_code == 201, retried.text


def test_imported_batch_cannot_be_deleted(client, owner_headers):
    _create_household(client, owner_headers)
    account = _create_account(client, owner_headers, opening_balance=0)
    category = _expense_category(client, owner_headers)
    batch = _upload(client, owner_headers, account["id"]).json()
    row = batch["rows"][0]
    client.patch(
        f"{PREFIX}/imports/{batch['id']}/rows/{row['id']}",
        headers=owner_headers,
        json={
            "revision": row["revision"],
            "status": "accepted",
            "category_id": category["id"],
        },
    )
    completed = client.post(
        f"{PREFIX}/imports/{batch['id']}/complete",
        headers=owner_headers,
        json={"revision": batch["revision"]},
    ).json()

    response = client.delete(
        f"{PREFIX}/imports/{batch['id']}?revision={completed['revision']}"
        f"&rows_revision={completed['rows_revision']}",
        headers=owner_headers,
    )

    assert response.status_code == 409
    assert client.get(
        f"{PREFIX}/imports/{batch['id']}", headers=owner_headers
    ).status_code == 200


def test_profiles_duplicates_and_household_isolation(client, owner_headers, outsider_headers):
    _create_household(client, owner_headers)
    account = _create_account(client, owner_headers, opening_balance=0)
    profile = client.post(
        f"{PREFIX}/import-profiles",
        headers=owner_headers,
        json={
            "name": "Bank CSV", "delimiter": ";", "encoding": "cp1252",
            "decimal_separator": ",", "date_format": "%d.%m.%Y",
            "mapping": {"booking_date": "Buchungstag", "debit_amount": "Soll", "credit_amount": "Haben"},
        },
    )
    assert profile.status_code == 201, profile.text
    assert client.get(f"{PREFIX}/import-profiles", headers=outsider_headers).status_code == 404

    first = _upload(client, owner_headers, account["id"])
    assert first.status_code == 201
    repeated_file = _upload(client, owner_headers, account["id"])
    assert repeated_file.status_code == 409
    same_transaction = _upload(client, owner_headers, account["id"], fixture="camt-v2.xml")
    assert same_transaction.status_code == 201
    assert same_transaction.json()["rows"][0]["status"] == "duplicate"
    assert client.get(f"{PREFIX}/imports/{first.json()['id']}", headers=outsider_headers).status_code == 404


def test_csv_upload_uses_explicit_mapping_and_creates_two_preview_rows(client, owner_headers):
    _create_household(client, owner_headers)
    account = _create_account(client, owner_headers, opening_balance=0)
    mapping = {
        "booking_date": "Buchungstag",
        "debit_amount": "Soll",
        "credit_amount": "Haben",
        "currency": "Waehrung",
        "counterparty": "Empfaenger",
        "purpose": "Zweck",
        "delimiter": ";",
        "encoding": "cp1252",
        "decimal_separator": ",",
        "date_format": "%d.%m.%Y",
    }

    response = _upload(
        client,
        owner_headers,
        account["id"],
        fixture="transactions.csv",
        format="csv",
        mapping=json.dumps(mapping),
    )

    assert response.status_code == 201, response.text
    assert [row["amount_minor"] for row in response.json()["rows"]] == [-1234, 250000]


def test_mixed_valid_and_invalid_csv_rows_create_reviewable_draft(client, owner_headers):
    _create_household(client, owner_headers)
    account = _create_account(client, owner_headers, opening_balance=0)
    mapping = {
        "booking_date": "Datum",
        "amount": "Betrag",
        "delimiter": ";",
        "encoding": "utf-8",
        "decimal_separator": ",",
        "date_format": "%d.%m.%Y",
    }
    payload = b"Datum;Betrag\n01.01.2026;-1,00\nkaputt;abc\n03.01.2026;-3,00"

    response = client.post(
        f"{PREFIX}/imports",
        headers=owner_headers,
        data={"account_id": str(account["id"]), "format": "csv", "mapping": json.dumps(mapping)},
        files={"file": ("mixed.csv", payload, "text/csv")},
    )

    assert response.status_code == 201, response.text
    assert [row["status"] for row in response.json()["rows"]] == ["pending", "error", "pending"]
    error_row = response.json()["rows"][1]
    assert error_row["errors"] == ["invalid_date"]

    category = _expense_category(client, owner_headers)
    corrected = client.patch(
        f"{PREFIX}/imports/{response.json()['id']}/rows/{error_row['id']}",
        headers=owner_headers,
        json={
            "revision": error_row["revision"],
            "booking_date": "2026-01-02",
            "amount_minor": -200,
            "currency": "EUR",
            "category_id": category["id"],
            "status": "accepted",
        },
    )
    assert corrected.status_code == 200, corrected.text
    assert corrected.json()["status"] == "accepted"
    assert corrected.json()["errors"] == []


def test_camt_batch_mismatch_cannot_be_cleared_by_editing_a_row(client, owner_headers):
    _create_household(client, owner_headers)
    account = _create_account(client, owner_headers, opening_balance=0)
    category = _expense_category(client, owner_headers)
    batch = _upload(
        client,
        owner_headers,
        account["id"],
        fixture="camt-batch-mismatch.xml",
    ).json()
    row = batch["rows"][0]

    response = client.patch(
        f"{PREFIX}/imports/{batch['id']}/rows/{row['id']}",
        headers=owner_headers,
        json={
            "revision": row["revision"],
            "booking_date": row["booking_date"],
            "amount_minor": row["amount_minor"],
            "currency": "EUR",
            "category_id": category["id"],
            "status": "accepted",
        },
    )

    assert response.status_code == 422
    unchanged = client.get(
        f"{PREFIX}/imports/{batch['id']}", headers=owner_headers
    ).json()["rows"][0]
    assert "camt_batch_amount_mismatch" in unchanged["errors"]


def test_csv_without_currency_column_uses_target_account_currency(client, owner_headers):
    household = client.post(
        f"{PREFIX}/household",
        headers=owner_headers,
        json={"name": "Schweiz", "base_currency": "CHF", "timezone": "Europe/Zurich"},
    )
    assert household.status_code == 201, household.text
    account = client.post(
        f"{PREFIX}/accounts",
        headers=owner_headers,
        json={"name": "CHF", "type": "checking", "currency": "CHF", "opening_balance": 0},
    ).json()
    mapping = {
        "booking_date": "Datum",
        "amount": "Betrag",
        "delimiter": ";",
        "encoding": "utf-8",
        "decimal_separator": ",",
        "date_format": "%d.%m.%Y",
    }
    response = client.post(
        f"{PREFIX}/imports",
        headers=owner_headers,
        data={"account_id": str(account["id"]), "format": "csv", "mapping": json.dumps(mapping)},
        files={"file": ("chf.csv", b"Datum;Betrag\n01.01.2026;-1,00", "text/csv")},
    )

    assert response.status_code == 201, response.text
    assert response.json()["rows"][0]["currency"] == "CHF"


def test_import_rejects_non_base_currency_target_accounts(client, owner_headers):
    _create_household(client, owner_headers)
    account_response = client.post(
        f"{PREFIX}/accounts",
        headers=owner_headers,
        json={"name": "USD", "type": "checking", "currency": "USD", "opening_balance": 0},
    )
    assert account_response.status_code == 201
    payload = (FIXTURES / "camt-v8.xml").read_bytes().replace(b'Ccy="EUR"', b'Ccy="USD"')

    response = client.post(
        f"{PREFIX}/imports",
        headers=owner_headers,
        data={"account_id": str(account_response.json()["id"]), "format": "camt"},
        files={"file": ("usd.xml", payload, "application/xml")},
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "import_base_currency_account_required"


def test_complete_rolls_back_all_rows_when_a_later_row_is_invalid(client, owner_headers):
    _create_household(client, owner_headers)
    account = _create_account(client, owner_headers, opening_balance=0)
    category = _expense_category(client, owner_headers)
    mapping = {
        "booking_date": "Buchungstag",
        "debit_amount": "Soll",
        "credit_amount": "Haben",
        "currency": "Waehrung",
        "delimiter": ";",
        "encoding": "cp1252",
        "decimal_separator": ",",
        "date_format": "%d.%m.%Y",
    }
    batch = _upload(
        client,
        owner_headers,
        account["id"],
        fixture="transactions.csv",
        format="csv",
        mapping=json.dumps(mapping),
    ).json()
    for row in batch["rows"]:
        changed = client.patch(
            f"{PREFIX}/imports/{batch['id']}/rows/{row['id']}",
            headers=owner_headers,
            json={"revision": row["revision"], "status": "accepted", "category_id": category["id"]},
        )
        assert changed.status_code == 200, changed.text

    response = client.post(
        f"{PREFIX}/imports/{batch['id']}/complete",
        headers=owner_headers,
        json={"revision": batch["revision"]},
    )

    assert response.status_code == 422
    assert client.get(f"{PREFIX}/transactions", headers=owner_headers).json() == []


def test_complete_is_atomic_balanced_and_reversible_once(client, owner_headers):
    _create_household(client, owner_headers)
    account = _create_account(client, owner_headers, opening_balance=0)
    category = _expense_category(client, owner_headers)
    batch = _upload(client, owner_headers, account["id"]).json()
    row = batch["rows"][0]

    accepted_without_category = client.patch(
        f"{PREFIX}/imports/{batch['id']}/rows/{row['id']}", headers=owner_headers,
        json={"revision": row["revision"], "status": "accepted"},
    )
    assert accepted_without_category.status_code == 200
    failed = client.post(
        f"{PREFIX}/imports/{batch['id']}/complete", headers=owner_headers,
        json={"revision": batch["revision"]},
    )
    assert failed.status_code == 422
    assert client.get(f"{PREFIX}/transactions", headers=owner_headers).json() == []

    selected = client.patch(
        f"{PREFIX}/imports/{batch['id']}/rows/{row['id']}", headers=owner_headers,
        json={"revision": accepted_without_category.json()["revision"], "category_id": category["id"]},
    )
    assert selected.status_code == 200, selected.text
    completed = client.post(
        f"{PREFIX}/imports/{batch['id']}/complete", headers=owner_headers,
        json={"revision": batch["revision"]},
    )
    assert completed.status_code == 200, completed.text
    imported_row = completed.json()["rows"][0]
    transaction = client.get(
        f"{PREFIX}/transactions/{imported_row['transaction_id']}", headers=owner_headers
    ).json()
    assert transaction["source"] == "import"
    assert sum(posting["base_amount"] for posting in transaction["postings"]) == 0

    reversed_batch = client.post(
        f"{PREFIX}/imports/{batch['id']}/reverse", headers=owner_headers,
        json={"revision": completed.json()["revision"]},
    )
    assert reversed_batch.status_code == 200, reversed_batch.text
    duplicate_reverse = client.post(
        f"{PREFIX}/imports/{batch['id']}/reverse", headers=owner_headers,
        json={"revision": reversed_batch.json()["revision"]},
    )
    assert duplicate_reverse.status_code == 409


def test_batch_reverse_tolerates_an_already_reversed_import_transaction(client, owner_headers):
    _create_household(client, owner_headers)
    account = _create_account(client, owner_headers, opening_balance=0)
    category = _expense_category(client, owner_headers)
    batch = _upload(client, owner_headers, account["id"]).json()
    row = batch["rows"][0]
    selected = client.patch(
        f"{PREFIX}/imports/{batch['id']}/rows/{row['id']}",
        headers=owner_headers,
        json={"revision": row["revision"], "status": "accepted", "category_id": category["id"]},
    ).json()
    completed = client.post(
        f"{PREFIX}/imports/{batch['id']}/complete",
        headers=owner_headers,
        json={"revision": batch["revision"]},
    ).json()
    transaction = client.get(
        f"{PREFIX}/transactions/{selected.get('transaction_id') or completed['rows'][0]['transaction_id']}",
        headers=owner_headers,
    ).json()
    manual_reverse = client.post(
        f"{PREFIX}/transactions/{transaction['id']}/reverse",
        headers=owner_headers,
        json={"revision": transaction["revision"]},
    )
    assert manual_reverse.status_code == 200, manual_reverse.text

    response = client.post(
        f"{PREFIX}/imports/{batch['id']}/reverse",
        headers=owner_headers,
        json={"revision": completed["revision"]},
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "reversed"
    assert response.json()["rows"][0]["status"] == "reversed"
