"""Tests für den PayPal-Aktivitäten-CSV-Import (Phase 2)."""

from __future__ import annotations

from conftest import PREFIX

from backend import import_paypal
from backend.import_parsers import ImportParseError, detect_format
from test_v1_api import _create_account, _create_household, _expense_category

_DE_HEADER = "Datum,Name,Typ,Status,Währung,Brutto,Entgelt,Transaktionscode\n"
_EN_HEADER = "Date,Name,Type,Status,Currency,Gross,Fee,Transaction ID\n"


def _de_csv(*rows: str) -> bytes:
    return (_DE_HEADER + "\n".join(rows) + "\n").encode("utf-8-sig")


def _en_csv(*rows: str) -> bytes:
    return (_EN_HEADER + "\n".join(rows) + "\n").encode("utf-8-sig")


# ---------------------------------------------------------------------------
# Parser-Logik direkt
# ---------------------------------------------------------------------------


def test_fee_is_split_into_its_own_row_with_colon_fee_reference():
    data = _de_csv(
        '01.03.2026,Max Mustermann,Zahlung empfangen,Abgeschlossen,EUR,"100,00","-3,50",TXN0001'
    )
    records = import_paypal.parse_paypal(data)
    assert len(records) == 2
    main, fee = records
    assert main.amount_minor == 10000
    assert type(main.amount_minor) is int
    assert main.bank_reference == "TXN0001"
    assert fee.amount_minor == -350
    assert fee.bank_reference == "TXN0001:fee"
    assert fee.purpose.startswith("PayPal-Gebühr")


def test_zero_fee_does_not_produce_a_second_row():
    data = _de_csv(
        '01.03.2026,Max Mustermann,Zahlung empfangen,Abgeschlossen,EUR,"100,00","0,00",TXN0002'
    )
    records = import_paypal.parse_paypal(data)
    assert len(records) == 1


def test_currency_conversion_rows_are_discarded_and_warn_previous_row():
    data = _de_csv(
        '01.03.2026,Max Mustermann,Zahlung empfangen,Abgeschlossen,EUR,"100,00","0,00",TXN0003',
        '01.03.2026,Allgemeine Währungsumrechnung,Allgemeine Währungsumrechnung,'
        'Abgeschlossen,EUR,"0,00","0,00",TXN0004',
    )
    records = import_paypal.parse_paypal(data)
    assert len(records) == 1
    assert records[0].bank_reference == "TXN0003"
    assert "paypal_currency_conversion_discarded" in records[0].warnings


def test_currency_conversion_english_header_is_also_discarded():
    data = _en_csv(
        '03/01/2026,John Doe,Payment Received,Completed,USD,"50.00","0.00",TXN1'
    )
    records = import_paypal.parse_paypal(data)
    assert len(records) == 1

    data_conversion = _en_csv(
        '03/01/2026,John Doe,Payment Received,Completed,USD,"50.00","0.00",TXN1',
        '03/01/2026,General Currency Conversion,General Currency Conversion,'
        'Completed,USD,"0.00","0.00",TXN2',
    )
    records2 = import_paypal.parse_paypal(data_conversion)
    assert len(records2) == 1
    assert "paypal_currency_conversion_discarded" in records2[0].warnings


def test_non_completed_status_becomes_error_row_not_pending():
    data = _de_csv(
        '03.03.2026,Shop GmbH,Zahlung gesendet,Ausstehend,EUR,"-20,00","0,00",TXN0005'
    )
    records = import_paypal.parse_paypal(data)
    assert len(records) == 1
    assert records[0].errors == ("paypal_status_not_completed",)
    assert records[0].amount_minor is None


def test_english_completed_status_is_accepted():
    data = _en_csv(
        '03/01/2026,John Doe,Payment Received,Completed,USD,"1,234.56","-35.00",TXN9001'
    )
    records = import_paypal.parse_paypal(data)
    assert len(records) == 2
    assert records[0].amount_minor == 123456
    assert records[0].currency == "USD"
    assert records[1].amount_minor == -3500


def test_foreign_currency_row_keeps_its_own_currency():
    data = _de_csv(
        '01.03.2026,Max Mustermann,Zahlung empfangen,Abgeschlossen,USD,"50,00","0,00",TXN0006'
    )
    records = import_paypal.parse_paypal(data)
    assert records[0].currency == "USD"


def test_cp1252_encoding_is_decoded():
    text = _DE_HEADER + (
        '01.03.2026,Käufer Müller,Zahlung empfangen,Abgeschlossen,EUR,"10,00","0,00",TXN0007\n'
    )
    data = text.encode("cp1252")
    records = import_paypal.parse_paypal(data)
    assert records[0].counterparty == "Käufer Müller"


def test_missing_required_column_raises_header_invalid():
    data = b"Foo,Bar\n1,2\n"
    try:
        import_paypal.parse_paypal(data)
        raise AssertionError("expected ImportParseError")
    except ImportParseError as exc:
        assert str(exc) == "paypal_header_invalid"


def test_detect_format_recognizes_paypal_header_both_languages():
    assert detect_format(_de_csv('01.03.2026,A,B,Abgeschlossen,EUR,"1,00","0,00",T1')) == "paypal"
    assert detect_format(_en_csv('03/01/2026,A,B,Completed,USD,"1.00","0.00",T1')) == "paypal"


# ---------------------------------------------------------------------------
# Ende-zu-Ende über die bestehende API: Dedup über Transaktionscode
# ---------------------------------------------------------------------------


def test_second_import_of_same_transaction_code_is_flagged_as_duplicate(
    client, owner_headers
):
    _create_household(client, owner_headers)
    account = _create_account(client, owner_headers, opening_balance=0)
    category = _expense_category(client, owner_headers)
    income_category = next(
        item
        for item in client.get(f"{PREFIX}/categories", headers=owner_headers).json()
        if item["kind"] == "income"
    )

    first_data = _de_csv(
        '01.03.2026,Max Mustermann,Zahlung empfangen,Abgeschlossen,EUR,"100,00","-3,50",TXN0001'
    )
    first = client.post(
        f"{PREFIX}/imports",
        headers=owner_headers,
        data={"account_id": str(account["id"]), "format": "paypal"},
        files={"file": ("paypal1.csv", first_data, "text/csv")},
    )
    assert first.status_code == 201, first.text
    first_batch = first.json()
    assert first_batch["source_format"] == "paypal"
    income_row = next(row for row in first_batch["rows"] if row["amount_minor"] == 10000)
    fee_row = next(row for row in first_batch["rows"] if row["amount_minor"] == -350)
    for row, cat in ((income_row, income_category), (fee_row, category)):
        client.patch(
            f"{PREFIX}/imports/{first_batch['id']}/rows/{row['id']}",
            headers=owner_headers,
            json={"revision": row["revision"], "status": "accepted", "category_id": cat["id"]},
        )
    completed = client.post(
        f"{PREFIX}/imports/{first_batch['id']}/complete",
        headers=owner_headers,
        json={"revision": first_batch["revision"]},
    )
    assert completed.status_code == 200, completed.text

    # Gleicher Transaktionscode, aber andere Datei (sonst würde schon der
    # Datei-Hash des Batches dedupen) - z.B. zusätzliche harmlose Leerzeile.
    second_data = _de_csv(
        '01.03.2026,Max Mustermann,Zahlung empfangen,Abgeschlossen,EUR,"100,00","-3,50",TXN0001',
        "",
    )
    second = client.post(
        f"{PREFIX}/imports",
        headers=owner_headers,
        data={"account_id": str(account["id"]), "format": "paypal"},
        files={"file": ("paypal2.csv", second_data, "text/csv")},
    )
    assert second.status_code == 201, second.text
    second_batch = second.json()
    income_row_2 = next(row for row in second_batch["rows"] if row["amount_minor"] == 10000)
    fee_row_2 = next(row for row in second_batch["rows"] if row["amount_minor"] == -350)
    assert income_row_2["status"] == "duplicate"
    assert fee_row_2["status"] == "duplicate"


def test_paypal_auto_detection_from_header(client, owner_headers):
    _create_household(client, owner_headers)
    account = _create_account(client, owner_headers, opening_balance=0)
    data = _de_csv(
        '01.03.2026,Max Mustermann,Zahlung empfangen,Abgeschlossen,EUR,"10,00","0,00",TXN0099'
    )
    response = client.post(
        f"{PREFIX}/imports",
        headers=owner_headers,
        data={"account_id": str(account["id"]), "format": "auto"},
        files={"file": ("activity.csv", data, "text/csv")},
    )
    assert response.status_code == 201, response.text
    assert response.json()["source_format"] == "paypal"


def test_foreign_currency_row_triggers_existing_account_currency_mismatch(
    client, owner_headers
):
    _create_household(client, owner_headers)
    account = _create_account(client, owner_headers, opening_balance=0)  # EUR-Konto
    data = _de_csv(
        '01.03.2026,Max Mustermann,Zahlung empfangen,Abgeschlossen,USD,"10,00","0,00",TXN0100'
    )
    response = client.post(
        f"{PREFIX}/imports",
        headers=owner_headers,
        data={"account_id": str(account["id"]), "format": "paypal"},
        files={"file": ("activity.csv", data, "text/csv")},
    )
    assert response.status_code == 201, response.text
    row = response.json()["rows"][0]
    assert row["status"] == "error"
    assert "account_currency_mismatch" in row["errors"]
