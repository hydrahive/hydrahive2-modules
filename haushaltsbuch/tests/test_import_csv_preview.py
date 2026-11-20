"""Tests für POST /imports/csv-preview (hb-bank-csv-notes.md) und die
detected_bank/detected_encoding-Felder der Batch-Antwort: Vorschau schreibt
nichts, Ownership/Größenlimit wie POST /imports.
"""

from __future__ import annotations

from pathlib import Path

from conftest import PREFIX
from test_v1_api import _create_account, _create_household

FIXTURES = Path(__file__).parent / "fixtures" / "bank_csv"


def _preview(client, headers, account_id, fixture: str):
    data = (FIXTURES / fixture).read_bytes()
    return client.post(
        f"{PREFIX}/imports/csv-preview",
        headers=headers,
        data={"account_id": str(account_id)},
        files={"file": ("umsaetze.csv", data, "text/csv")},
    )


def test_preview_known_bank_detects_header_and_encoding_without_writing(client, owner_headers):
    _create_household(client, owner_headers)
    account = _create_account(client, owner_headers, opening_balance=0)

    response = _preview(client, owner_headers, account["id"], "sparkasse_mt940.csv")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["encoding"] == "cp1252"
    assert body["delimiter"] == ";"
    assert body["bank"] == {"id": "sparkasse_mt940", "label": "Sparkasse – CSV-MT940"}
    assert "Buchungstag" in body["header"]
    assert len(body["sample_rows"]) == 2  # beide Datenzeilen der Fixture

    # Schreibt nichts - keine Batches entstanden.
    batches = client.get(f"{PREFIX}/imports", headers=owner_headers).json()
    assert batches == []


def test_preview_unknown_bank_shows_columns_for_mapping_dialog(client, owner_headers):
    """Unbekannte Bank: kein `bank`, aber Kopfzeile/Spalten trotzdem erkannt
    (für die Vorbelegung des Zuordnungsdialogs)."""
    _create_household(client, owner_headers)
    account = _create_account(client, owner_headers, opening_balance=0)
    data = b"Datum;Betrag;Partner\n01.01.2026;10,00;Irgendwer\n"

    response = client.post(
        f"{PREFIX}/imports/csv-preview", headers=owner_headers,
        data={"account_id": str(account["id"])},
        files={"file": ("export.csv", data, "text/csv")},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["bank"] is None
    assert body["header"] == ["Datum", "Betrag", "Partner"]
    assert body["sample_rows"] == [["01.01.2026", "10,00", "Irgendwer"]]


def test_preview_respects_ownership_like_imports(client, owner_headers, outsider_headers):
    _create_household(client, owner_headers)
    account = _create_account(client, owner_headers, opening_balance=0)

    response = _preview(client, outsider_headers, account["id"], "sparkasse_mt940.csv")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "household_not_found"


def test_preview_rejects_archived_account_like_imports(client, owner_headers):
    _create_household(client, owner_headers)
    account = _create_account(client, owner_headers, opening_balance=0)
    client.put(
        f"{PREFIX}/accounts/{account['id']}", headers=owner_headers,
        json={
            "name": account["name"], "type": account["type"], "owner_member_id": None,
            "bank_identifier": None, "archived": True, "revision": account["revision"],
        },
    )

    response = _preview(client, owner_headers, account["id"], "sparkasse_mt940.csv")
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "account_archived"


def test_preview_rejects_oversized_file_like_imports(client, owner_headers):
    from backend.import_parsers import MAX_FILE_SIZE

    _create_household(client, owner_headers)
    account = _create_account(client, owner_headers, opening_balance=0)
    oversized = b"a;b\n" + b"1;2\n" * (MAX_FILE_SIZE // 4 + 1)

    response = client.post(
        f"{PREFIX}/imports/csv-preview", headers=owner_headers,
        data={"account_id": str(account["id"])},
        files={"file": ("gross.csv", oversized, "text/csv")},
    )
    # _read_limited() (wie bei POST /imports) bricht beim Lesen ab -> 413,
    # bevor preview_csv() überhaupt check_file_size() erreicht.
    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "file_too_large"


def test_batch_response_has_detected_bank_and_encoding(client, owner_headers):
    data = (FIXTURES / "dkb.csv").read_bytes()
    _create_household(client, owner_headers)
    account = _create_account(client, owner_headers, opening_balance=0)

    created = client.post(
        f"{PREFIX}/imports", headers=owner_headers,
        data={"account_id": str(account["id"]), "format": "auto"},
        files={"file": ("dkb.csv", data, "text/csv")},
    )
    assert created.status_code == 201, created.text
    batch_id = created.json()["id"]
    assert created.json()["detected_bank"] == {"id": "dkb", "label": "DKB"}
    assert created.json()["detected_encoding"] == "utf-8-sig"

    # GET /imports/{id} liefert dieselben Felder (persistiert, nicht nur Antwort des POST).
    fetched = client.get(f"{PREFIX}/imports/{batch_id}", headers=owner_headers).json()
    assert fetched["detected_bank"] == {"id": "dkb", "label": "DKB"}
    assert fetched["detected_encoding"] == "utf-8-sig"


def test_batch_response_detected_bank_is_null_for_explicit_mapping(client, owner_headers):
    """Mit expliziter Feldzuordnung (kein Auto-Erkennungsweg) bleibt
    detected_bank null - der Nutzer hat selbst zugeordnet."""
    _create_household(client, owner_headers)
    account = _create_account(client, owner_headers, opening_balance=0)
    data = (FIXTURES / "sparkasse_mt940.csv").read_bytes()
    import json

    mapping = {
        "booking_date": "Buchungstag", "amount": "Betrag", "currency": "Waehrung",
        "counterparty": "Beguenstigter/Zahlungspflichtiger", "purpose": "Verwendungszweck",
        "encoding": "cp1252", "date_format": "%d.%m.%y",
    }
    created = client.post(
        f"{PREFIX}/imports", headers=owner_headers,
        data={"account_id": str(account["id"]), "format": "csv", "mapping": json.dumps(mapping)},
        files={"file": ("export.csv", data, "text/csv")},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["detected_bank"] is None
    assert body["detected_encoding"] == "cp1252"
