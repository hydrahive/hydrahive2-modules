from __future__ import annotations

from pathlib import Path

import pytest

from backend.import_parsers import (
    MAX_FILE_SIZE,
    MAX_RECORDS,
    CsvMapping,
    ImportParseError,
    detect_format,
    parse_import,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_detects_supported_formats():
    assert detect_format((FIXTURES / "camt-v8.xml").read_bytes(), "x.xml") == "camt"
    assert detect_format((FIXTURES / "transactions.mt940").read_bytes(), "x.txt") == "mt940"
    assert detect_format((FIXTURES / "transactions.csv").read_bytes(), "x.csv") == "csv"


def test_camt_v2_and_v8_normalize_to_same_records():
    v2 = parse_import((FIXTURES / "camt-v2.xml").read_bytes(), "camt")
    v8 = parse_import((FIXTURES / "camt-v8.xml").read_bytes(), "camt")
    assert v2 == v8
    assert v8[0].amount_minor == -1234
    assert v8[0].counterparty_identifier == "****3000"


@pytest.mark.parametrize("declaration", [b"<!DOCTYPE Document []>", b"<!ENTITY x SYSTEM 'file:///etc/passwd'>"])
def test_camt_rejects_dtd_and_entities(declaration):
    payload = b"<?xml version='1.0'?>" + declaration + b"<Document/>"
    with pytest.raises(ImportParseError, match="xml_declaration_forbidden"):
        parse_import(payload, "camt")


def test_camt_splits_batch_details_and_uses_directional_counterparty():
    xml = '''<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.08"><BkToCstmrStmt><Stmt><Ntry>
<Amt Ccy="EUR">30.00</Amt><CdtDbtInd>DBIT</CdtDbtInd><BookgDt><Dt>2026-07-17</Dt></BookgDt>
<NtryDtls>
<TxDtls><AmtDtls><TxAmt><Amt Ccy="EUR">10.00</Amt></TxAmt></AmtDtls><RltdPties><Dbtr><Pty><Nm>Eigenname</Nm></Pty></Dbtr><Cdtr><Pty><Nm>Händler A</Nm></Pty></Cdtr></RltdPties><RmtInf><Ustrd>A</Ustrd></RmtInf></TxDtls>
<TxDtls><AmtDtls><TxAmt><Amt Ccy="EUR">20.00</Amt></TxAmt></AmtDtls><RltdPties><Dbtr><Pty><Nm>Eigenname</Nm></Pty></Dbtr><Cdtr><Pty><Nm>Händler B</Nm></Pty></Cdtr></RltdPties><RmtInf><Ustrd>B</Ustrd></RmtInf></TxDtls>
</NtryDtls></Ntry></Stmt></BkToCstmrStmt></Document>'''.encode()

    rows = parse_import(xml, "camt")

    assert [(row.amount_minor, row.counterparty) for row in rows] == [
        (-1000, "Händler A"),
        (-2000, "Händler B"),
    ]


def test_camt_batch_amount_mismatch_remains_a_structural_error():
    rows = parse_import((FIXTURES / "camt-batch-mismatch.xml").read_bytes(), "camt")

    assert len(rows) == 2
    assert all(row.errors == ("camt_batch_amount_mismatch",) for row in rows)


def test_mt940_reversal_signs_and_entry_dates_are_normalized():
    mt940 = b''':20:X
:60F:C251230EUR0,00
:61:2512310102RD1,00NTRFNONREF//NONREF
:86:SVWZ+Ruecklastschrift
:61:2601021231RC2,00NTRFNONREF//NONREF
:86:SVWZ+Storno Gutschrift
:62F:D260102EUR1,00'''

    rows = parse_import(mt940, "mt940")

    assert (rows[0].amount_minor, rows[0].booking_date.isoformat(), rows[0].value_date.isoformat()) == (
        100,
        "2026-01-02",
        "2025-12-31",
    )
    assert (rows[1].amount_minor, rows[1].booking_date.isoformat(), rows[1].value_date.isoformat()) == (
        -200,
        "2025-12-31",
        "2026-01-02",
    )


def test_csv_keeps_invalid_rows_as_reviewable_errors():
    payload = b"Datum;Betrag\n01.01.2026;1,00\nkaputt;abc\n03.01.2026;3,00"
    mapping = CsvMapping(booking_date="Datum", amount="Betrag", date_format="%d.%m.%Y", delimiter=";")

    rows = parse_import(payload, "csv", mapping)

    assert len(rows) == 3
    assert rows[0].errors == ()
    assert rows[1].errors == ("invalid_date",)
    assert rows[2].amount_minor == 300


def test_mt940_and_csv_are_normalized():
    mt940 = parse_import((FIXTURES / "transactions.mt940").read_bytes(), "mt940")
    assert mt940[0].amount_minor == -1234
    assert "Einkauf" in mt940[0].purpose

    mapping = CsvMapping(
        booking_date="Buchungstag",
        debit_amount="Soll",
        credit_amount="Haben",
        currency="Waehrung",
        counterparty="Empfaenger",
        purpose="Zweck",
        date_format="%d.%m.%Y",
        delimiter=";",
        encoding="cp1252",
        decimal_separator=",",
    )
    csv_rows = parse_import((FIXTURES / "transactions.csv").read_bytes(), "csv", mapping)
    assert csv_rows[0].amount_minor == -1234
    assert csv_rows[1].amount_minor == 250000


def test_placeholder_bank_references_do_not_create_strong_fingerprints():
    mt940 = b":20:X\n:60F:C250101EUR0,00\n:61:250102D1,00NTRFNONREF//NONREF\n:86:SVWZ+Test\n:62F:D250102EUR1,00"
    record = parse_import(mt940, "mt940")[0]
    assert record.bank_reference is None

    camt = (FIXTURES / "camt-v8.xml").read_text().replace(
        "<AcctSvcrRef>REF-1</AcctSvcrRef>",
        "<NtryDtls><TxDtls><Refs><EndToEndId>NOTPROVIDED</EndToEndId></Refs></TxDtls></NtryDtls>",
    )
    assert parse_import(camt.encode(), "camt")[0].bank_reference is None


def test_utf16_xml_is_rejected_before_elementtree_parsing():
    payload = "<?xml version='1.0'?><!DOCTYPE Document []><Document/>".encode("utf-16")
    with pytest.raises(ImportParseError, match="invalid_xml_encoding"):
        parse_import(payload, "camt")


def test_limits_are_enforced_before_parsing():
    with pytest.raises(ImportParseError, match="file_too_large"):
        parse_import(b"x" * (MAX_FILE_SIZE + 1), "mt940")
    rows = "Datum;Betrag\n" + "\n".join("01.01.2025;1,00" for _ in range(MAX_RECORDS + 1))
    mapping = CsvMapping(booking_date="Datum", amount="Betrag", date_format="%d.%m.%Y", delimiter=";")
    with pytest.raises(ImportParseError, match="too_many_records"):
        parse_import(rows.encode(), "csv", mapping)
