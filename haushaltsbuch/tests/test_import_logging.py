"""Tests für das Server-Log bei abgelehnten Imports (hb-bank-csv-notes.md):
jeder ImportParseError (-> 422 in create_batch) UND jeder coded()-Fehler aus
validate_upload_target/Mapping-Parsing/create_batch wird zentral in der
Route POST /imports geloggt - mit Code, Format und Dateiendung, OHNE
Dateiinhalt und ohne vollen Dateinamen.
"""

from __future__ import annotations

import logging

from conftest import PREFIX
from test_v1_api import _create_account, _create_household


def _upload(client, headers, account_id, *, filename="umsaetze.unbekannt", content=b"keine;csv;hier", fmt="auto"):
    return client.post(
        f"{PREFIX}/imports",
        headers=headers,
        data={"account_id": str(account_id), "format": fmt},
        files={"file": (filename, content, "text/csv")},
    )


def test_unsupported_format_is_logged_with_code_format_and_extension(client, owner_headers, caplog):
    _create_household(client, owner_headers)
    account = _create_account(client, owner_headers, opening_balance=0)

    with caplog.at_level(logging.WARNING, logger="backend.import_inbox"):
        response = _upload(client, owner_headers, account["id"], filename="geheime-rechnung.pdf.unbekannt", content=b"\x00\x01")
    assert response.status_code == 422
    code = response.json()["detail"]["code"]
    assert code == "unsupported_format"

    [record] = [r for r in caplog.records if "import abgelehnt" in r.message]
    assert f"code={code}" in record.message
    assert ".unbekannt" in record.message
    # Kein Dateiinhalt, kein voller Dateiname im Log.
    assert "geheime-rechnung" not in record.message
    assert "\\x00" not in record.message


def test_csv_mapping_required_is_logged(client, owner_headers, caplog):
    """Unbekannte CSV-Bank ohne Zuordnung -> csv_mapping_required, ebenfalls
    geloggt (nicht nur ImportParseError-Codes, die direkt aus den Parsern
    kommen, sondern auch dieser spezielle Fall aus parse_import selbst)."""
    _create_household(client, owner_headers)
    account = _create_account(client, owner_headers, opening_balance=0)

    with caplog.at_level(logging.WARNING, logger="backend.import_inbox"):
        response = _upload(
            client, owner_headers, account["id"], filename="export.csv",
            content=b"Spalte A;Spalte B\nx;y\n",
        )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "csv_mapping_required"
    [record] = [r for r in caplog.records if "import abgelehnt" in r.message]
    assert "code=csv_mapping_required" in record.message
    assert "format=csv" in record.message
    assert ".csv" in record.message


def test_account_archived_is_logged(client, owner_headers, caplog):
    _create_household(client, owner_headers)
    account = _create_account(client, owner_headers, opening_balance=0)
    archived = client.put(
        f"{PREFIX}/accounts/{account['id']}", headers=owner_headers,
        json={
            "name": account["name"], "type": account["type"], "owner_member_id": None,
            "bank_identifier": None, "archived": True, "revision": account["revision"],
        },
    ).json()
    assert archived["archived"] is True

    with caplog.at_level(logging.WARNING, logger="backend.import_inbox"):
        response = _upload(client, owner_headers, account["id"], filename="x.csv")
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "account_archived"
    [record] = [r for r in caplog.records if "import abgelehnt" in r.message]
    assert "code=account_archived" in record.message


def test_successful_import_logs_nothing(client, owner_headers, caplog):
    """Gegenstück: ein erfolgreicher Import erzeugt KEINE Ablehnungs-Logzeile."""
    from pathlib import Path

    fixture = (Path(__file__).parent / "fixtures" / "bank_csv" / "dkb.csv").read_bytes()
    _create_household(client, owner_headers)
    account = _create_account(client, owner_headers, opening_balance=0)

    with caplog.at_level(logging.WARNING, logger="backend.import_inbox"):
        response = client.post(
            f"{PREFIX}/imports", headers=owner_headers,
            data={"account_id": str(account["id"]), "format": "auto"},
            files={"file": ("dkb.csv", fixture, "text/csv")},
        )
    assert response.status_code == 201, response.text
    assert [r for r in caplog.records if "import abgelehnt" in r.message] == []
