"""Tests für die Bank-CSV-Erkennung (hb-bank-csv-notes.md): Erkennung je
Bank per Kopfzeile (Modulebene) + der komplette Weg über POST /imports mit
format="auto" und OHNE Feldzuordnung (API-Ebene).

Fixtures unter tests/fixtures/bank_csv/ - eigene, kleine Nachbauten mit
demselben Spaltenaufbau/Zeichensatz/Datumsformat wie die belegten
AGPL-Vorlagen (github.com/nicolettas-muggelbude/RechnungsFee), NICHT
1:1 kopiert (Lizenz).
"""

from __future__ import annotations

from pathlib import Path

from backend.import_bank_csv_rewrite import parse_bank_csv
from conftest import PREFIX
from test_v1_api import _create_account, _create_household

FIXTURES = Path(__file__).parent / "fixtures" / "bank_csv"


# ---------------------------------------------------------------------------
# Modulebene: je Bank Zeilenzahl, ein Betrag in Cent, Datum, Gegenpartei,
# Zeichensatz, Besonderheiten (vorgemerkt/Betrag 0/Fußzeile).
# ---------------------------------------------------------------------------


def test_sparkasse_mt940_cp1252_umlaut_and_pending():
    data = (FIXTURES / "sparkasse_mt940.csv").read_bytes()
    records, template, encoding = parse_bank_csv(data)
    assert template.id == "sparkasse_mt940"
    assert encoding == "cp1252"
    assert len(records) == 2
    gutschrift, lastschrift = records
    assert gutschrift.amount_minor == 4200
    assert gutschrift.booking_date.isoformat() == "2026-11-10"
    assert gutschrift.counterparty == "Muster GmbH"
    assert gutschrift.errors == ()
    assert "Müllheim" in lastschrift.counterparty
    assert lastschrift.amount_minor == -1337
    assert "pending_transaction" in lastschrift.errors  # Info "Umsatz vorgemerkt"


def test_sparkasse_camt_utf8_sig():
    data = (FIXTURES / "sparkasse_camt.csv").read_bytes()
    records, template, encoding = parse_bank_csv(data)
    assert template.id == "sparkasse_camt"
    assert encoding == "utf-8-sig"
    assert len(records) == 1
    assert records[0].amount_minor == -50000
    assert records[0].counterparty == "Vermieter GmbH"
    assert records[0].booking_date.isoformat() == "2026-11-10"


def test_genossenschaftsbank_utf8_sig_bom():
    """VR/Sparda/GLS gemeinsames Format (18 Spalten)."""
    data = (FIXTURES / "genossenschaft.csv").read_bytes()
    records, template, encoding = parse_bank_csv(data)
    assert template.id == "genossenschaft"
    assert encoding == "utf-8-sig"
    assert len(records) == 1
    assert records[0].amount_minor == -2550
    assert records[0].counterparty == "Test Partner"
    assert records[0].booking_date.isoformat() == "2026-11-10"


def test_ing_cp1252_metadata_header_at_line_13():
    data = (FIXTURES / "ing.csv").read_bytes()
    records, template, encoding = parse_bank_csv(data)
    assert template.id == "ing"
    assert encoding == "cp1252"
    assert len(records) == 1
    assert records[0].amount_minor == -1999
    assert records[0].counterparty == "Test Firma"
    assert records[0].booking_date.isoformat() == "2026-11-10"


def test_dkb_utf8_sig_counterparty_by_direction_and_pending_status():
    data = (FIXTURES / "dkb.csv").read_bytes()
    records, template, encoding = parse_bank_csv(data)
    assert template.id == "dkb"
    assert encoding == "utf-8-sig"
    assert len(records) == 3
    eingang, ausgang, vorgemerkt = records
    # DKB-Gegenpartei: Eingang -> Zahlungspflichtige*r, Ausgang -> Zahlungsempfänger*in.
    assert eingang.amount_minor == 20000
    assert eingang.counterparty == "Test Nutzer"
    assert ausgang.amount_minor == -3321
    assert ausgang.counterparty == "Testfirma"
    assert vorgemerkt.amount_minor == -500
    assert "pending_transaction" in vorgemerkt.errors  # Status "Vorgemerkt"


def test_commerzbank_utf8_sig_skips_zero_amount_info_row():
    data = (FIXTURES / "commerzbank.csv").read_bytes()
    records, template, encoding = parse_bank_csv(data)
    assert template.id == "commerzbank"
    assert encoding == "utf-8-sig"
    # 2 Zeilen in der Fixture, davon 1 mit Betrag 0 (Infozeile) -> übersprungen.
    assert len(records) == 1
    assert records[0].amount_minor == -1850


def test_postbank_utf8_sig_date_without_leading_zero_and_footer_ignored():
    data = (FIXTURES / "postbank.csv").read_bytes()
    records, template, encoding = parse_bank_csv(data)
    assert template.id == "postbank"
    assert encoding == "utf-8-sig"
    # 2 Buchungszeilen + 1 Kontostand-Fußzeile in der Fixture -> Fußzeile raus.
    assert len(records) == 2
    gutschrift, kartenzahlung = records
    assert gutschrift.amount_minor == 7500
    assert gutschrift.booking_date.isoformat() == "2026-11-02"  # "2.11.2026" ohne führende Null
    assert kartenzahlung.amount_minor == -999
    assert kartenzahlung.counterparty == "Testladen"


# ---------------------------------------------------------------------------
# API-Ebene: POST /imports, format="auto", KEINE Feldzuordnung.
# ---------------------------------------------------------------------------


def _upload_bank_csv(client, headers, account_id, fixture: str):
    data = (FIXTURES / fixture).read_bytes()
    return client.post(
        f"{PREFIX}/imports",
        headers=headers,
        data={"account_id": str(account_id), "format": "auto"},
        files={"file": ("umsaetze.csv", data, "text/csv")},
    )


def test_auto_format_no_mapping_sparkasse_mt940_like_buddys_file(client, owner_headers):
    """Buddys Datei (.work/etappe-a/sparkasse-csv-mt940-test.csv): cp1252,
    TT.MM.JJ, 2 Zeilen, ohne Feldzuordnung -> 201."""
    _create_household(client, owner_headers)
    account = _create_account(client, owner_headers, opening_balance=0)

    response = _upload_bank_csv(client, owner_headers, account["id"], "sparkasse_mt940.csv")
    assert response.status_code == 201, response.text
    batch = response.json()
    assert batch["source_format"] == "csv"
    assert batch["detected_bank"] == {"id": "sparkasse_mt940", "label": "Sparkasse – CSV-MT940"}
    assert batch["detected_encoding"] == "cp1252"
    assert len(batch["rows"]) == 2
    assert batch["rows"][0]["amount_minor"] == 4200
    assert batch["rows"][1]["errors"] == ["pending_transaction"]


def test_auto_format_no_mapping_dkb(client, owner_headers):
    _create_household(client, owner_headers)
    account = _create_account(client, owner_headers, opening_balance=0)

    response = _upload_bank_csv(client, owner_headers, account["id"], "dkb.csv")
    assert response.status_code == 201, response.text
    batch = response.json()
    assert batch["detected_bank"]["id"] == "dkb"
    assert batch["detected_encoding"] == "utf-8-sig"
    assert len(batch["rows"]) == 3


# ---------------------------------------------------------------------------
# Gegenproben: Erkennung aus -> Test rot.
# ---------------------------------------------------------------------------


def test_counterproof_bank_detection_disabled_falls_back_to_mapping_required(client, owner_headers, monkeypatch):
    """Ohne die Bank-Erkennung (parse_bank_csv liefert immer None) schlägt
    derselbe Upload mit csv_mapping_required fehl statt mit 201 zu erkennen -
    zeigt, dass die Erkennung tatsächlich der Grund für den Erfolg ist."""
    import backend.import_parsers as import_parsers_module

    monkeypatch.setattr(
        "backend.import_bank_csv_rewrite.parse_bank_csv", lambda data: None,
    )
    _create_household(client, owner_headers)
    account = _create_account(client, owner_headers, opening_balance=0)

    response = _upload_bank_csv(client, owner_headers, account["id"], "sparkasse_mt940.csv")
    assert response.status_code == 422, response.text
    assert response.json()["detail"]["code"] == "csv_mapping_required"
    del import_parsers_module  # nur zur Doku, dass der Patch das lazy import trifft


def test_counterproof_encoding_detection_disabled_rejects_cp1252_file(client, owner_headers, monkeypatch):
    """Ohne die Zeichensatz-Erkennung (detect_encoding wirft immer
    invalid_encoding) kann detect_bank_template() die Kopfzeile nicht mehr
    lesen und liefert None (fail-closed, kein Erraten) -> derselbe Upload
    landet beim alten Zuordnungsweg (csv_mapping_required) statt beim
    201-Erfolg - zeigt, dass die automatische Zeichensatz-Erkennung der
    Grund ist, warum cp1252-Dateien ohne explizite Angabe funktionieren.

    import_bank_csv_rewrite importiert detect_encoding direkt (from
    .import_csv import detect_encoding) - patchen muss daher am
    Verwendungsort ansetzen, nicht am Modul import_csv selbst (sonst bleibt
    die alte Funktion lokal gebunden und der Patch greift nicht)."""
    def _raise(data):
        from backend.import_parsers import ImportParseError

        raise ImportParseError("invalid_encoding")

    monkeypatch.setattr("backend.import_bank_csv_rewrite.detect_encoding", _raise)
    _create_household(client, owner_headers)
    account = _create_account(client, owner_headers, opening_balance=0)

    response = _upload_bank_csv(client, owner_headers, account["id"], "sparkasse_mt940.csv")
    assert response.status_code == 422, response.text
    assert response.json()["detail"]["code"] == "csv_mapping_required"
