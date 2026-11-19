"""Tests für den PDF-Kontoauszug-Import (Phase 2).

Synthetische PDFs werden im Test selbst erzeugt (minimale, handgeschriebene
PDF-Objektstruktur mit einem Textobjekt bzw. ganz ohne Contents) - kein
externes Fixture-Binary, keine Abhängigkeit von einem PDF-Erzeugungspaket.

Die Ende-zu-Ende-Tests (Upload -> Vorschau -> complete) laufen über die
echte Sandbox (pdfinfo/pdftotext via bwrap+prlimit) und werden nur
übersprungen, wenn diese Werkzeuge auf dem Testsystem fehlen. Die
Parser-Logik selbst (Zeilenerkennung, Datum/Betrag, Jahr-Heuristik) wird
zusätzlich mit einer gemockten Extraktion getestet, damit die Suite auch
ohne Poppler etwas über den Parser prüft.
"""

from __future__ import annotations

import shutil
from datetime import date

import pytest
from conftest import PREFIX

from backend import import_pdf
from backend.import_parsers import ImportParseError
from test_v1_api import _create_account, _create_household, _expense_category

_SANDBOX_AVAILABLE = all(
    shutil.which(name) for name in ("pdftotext", "pdfinfo", "bwrap", "prlimit")
)
requires_sandbox = pytest.mark.skipif(
    not _SANDBOX_AVAILABLE, reason="pdftotext/pdfinfo/bwrap nicht verfügbar"
)


def _pdf_with_text(lines: list[str]) -> bytes:
    """Minimales handgeschriebenes PDF mit einem Textobjekt (ein Tj je Zeile)."""
    y = 750
    parts = []
    for line in lines:
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        parts.append(f"BT /F1 10 Tf 50 {y} Td ({escaped}) Tj ET")
        y -= 14
    content = "\n".join(parts).encode("latin-1")
    objects = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj",
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj",
        b"3 0 obj << /Type /Page /Parent 2 0 R /Resources << /Font << /F1 5 0 R >> >> "
        b"/MediaBox [0 0 612 792] /Contents 4 0 R >> endobj",
        b"4 0 obj << /Length %d >>\nstream\n%s\nendstream endobj" % (len(content), content),
        b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj",
    ]
    return _assemble_pdf(objects)


def _pdf_without_text() -> bytes:
    """Minimales PDF mit einer Seite ganz ohne Contents (kein Textobjekt)."""
    objects = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj",
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj",
        b"3 0 obj << /Type /Page /Parent 2 0 R /Resources << >> /MediaBox [0 0 612 792] >> endobj",
    ]
    return _assemble_pdf(objects)


def _assemble_pdf(objects: list[bytes]) -> bytes:
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(out))
        out += obj + b"\n"
    xref_offset = len(out)
    out += b"xref\n0 %d\n" % (len(objects) + 1)
    out += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        out += b"%010d 00000 n \n" % offset
    out += b"trailer << /Size %d /Root 1 0 R >>\n" % (len(objects) + 1)
    out += b"startxref\n%d\n%%%%EOF" % xref_offset
    return bytes(out)


_STATEMENT_LINES = [
    "Kontoauszug Nr. 3/2026  01.03.2026 - 31.03.2026",
    "01.03. 02.03. Miete Max Mustermann -850,00",
    "Verwendungszweck: Miete Maerz 2026",
    "15.03. 15.03. Gehalt Arbeitgeber GmbH 2.500,00 H",
    "28.03. 29.03. Unklare Buchung ohne Betrag",
]


# ---------------------------------------------------------------------------
# Parser-Logik direkt (ohne Sandbox-Abhängigkeit, läuft immer)
# ---------------------------------------------------------------------------


def test_parse_text_recognizes_lines_amounts_and_continuations():
    text = "\n".join(_STATEMENT_LINES)
    records = import_pdf._parse_text(text)
    assert len(records) == 3

    rent = records[0]
    assert rent.booking_date == date(2026, 3, 1)
    assert rent.value_date == date(2026, 3, 2)
    assert rent.amount_minor == -85000
    assert rent.currency == "EUR"
    assert rent.purpose == "Miete Max Mustermann Miete Maerz 2026"
    assert rent.errors == ()

    salary = records[1]
    assert salary.booking_date == date(2026, 3, 15)
    assert salary.amount_minor == 250000
    assert type(salary.amount_minor) is int

    ambiguous = records[2]
    assert ambiguous.errors == ("pdf_line_ambiguous",)
    assert ambiguous.amount_minor is None
    assert ambiguous.booking_date is None


def test_parse_text_without_statement_period_cannot_resolve_two_digit_year():
    # Ohne den Zeitraum-Header im Kopf kann "TT.MM." nicht ins Jahr aufgelöst
    # werden -> die Zeile ist unklar statt geraten.
    text = "01.03. Unklare Zeile ohne Jahreskontext 10,00"
    records = import_pdf._parse_text(text)
    assert len(records) == 1
    assert records[0].errors == ("pdf_line_ambiguous",)


def test_parse_amount_requires_explicit_sign_or_sh_suffix():
    assert import_pdf._parse_amount("10,00", None, None) is None
    assert import_pdf._parse_amount("10,00", "-", None) == -1000
    assert import_pdf._parse_amount("10,00", "+", None) == 1000
    assert import_pdf._parse_amount("10,00", None, "S") == -1000
    assert import_pdf._parse_amount("10,00", None, "H") == 1000


def test_parse_pdf_with_mocked_extraction_reaches_too_many_pages_and_no_text_layer(
    monkeypatch,
):
    monkeypatch.setattr(import_pdf, "_page_count", lambda path, work: 51)
    with pytest.raises(ImportParseError) as excinfo:
        import_pdf.parse_pdf(b"%PDF-1.4 fake")
    assert str(excinfo.value) == "pdf_too_many_pages"

    monkeypatch.setattr(import_pdf, "_page_count", lambda path, work: 1)
    monkeypatch.setattr(import_pdf, "_extract_text", lambda path, pages, work: "x")
    with pytest.raises(ImportParseError) as excinfo:
        import_pdf.parse_pdf(b"%PDF-1.4 fake")
    assert str(excinfo.value) == "pdf_no_text_layer"


def test_parse_pdf_with_mocked_extraction_detects_no_transactions(monkeypatch):
    monkeypatch.setattr(import_pdf, "_page_count", lambda path, work: 1)
    monkeypatch.setattr(
        import_pdf, "_extract_text", lambda path, pages, work: "Kontoauszug ohne Buchungszeilen " * 3
    )
    with pytest.raises(ImportParseError) as excinfo:
        import_pdf.parse_pdf(b"%PDF-1.4 fake")
    assert str(excinfo.value) == "pdf_no_transactions"


def test_sandbox_unavailable_is_fail_closed_not_a_fallback(monkeypatch):
    from hydrahive.tools import _document_process

    def _raise_isolation_error(*args, **kwargs):
        raise _document_process.DocumentIsolationError("bwrap fehlt")

    monkeypatch.setattr(import_pdf._document_process, "run", _raise_isolation_error)
    with pytest.raises(ImportParseError) as excinfo:
        import_pdf.parse_pdf(b"%PDF-1.4 fake")
    assert str(excinfo.value) == "pdf_extraction_unavailable"


def test_work_directory_is_private_and_removed_afterwards(monkeypatch):
    created_dirs: list = []
    real_private = import_pdf._private_work_dir

    def _tracking_private_work_dir():
        work_root = real_private()
        created_dirs.append(work_root)
        return work_root

    monkeypatch.setattr(import_pdf, "_private_work_dir", _tracking_private_work_dir)
    monkeypatch.setattr(import_pdf, "_page_count", lambda path, work: 1)
    monkeypatch.setattr(import_pdf, "_extract_text", lambda path, pages, work: "x" * 30)
    monkeypatch.setattr(import_pdf, "_parse_text", lambda text: [])
    with pytest.raises(ImportParseError):
        import_pdf.parse_pdf(b"%PDF-1.4 fake")
    assert created_dirs, "privates Arbeitsverzeichnis wurde nicht angelegt"
    assert not created_dirs[0].exists(), "Arbeitsverzeichnis wurde nicht gelöscht"


# ---------------------------------------------------------------------------
# Echte Sandbox-Extraktion (nur wenn pdftotext/pdfinfo/bwrap vorhanden sind)
# ---------------------------------------------------------------------------


@requires_sandbox
def test_parse_pdf_extracts_via_real_sandbox():
    data = _pdf_with_text(_STATEMENT_LINES)
    records = import_pdf.parse_pdf(data)
    assert len(records) == 3
    assert records[0].amount_minor == -85000
    assert records[1].amount_minor == 250000
    assert records[2].errors == ("pdf_line_ambiguous",)


@requires_sandbox
def test_scan_pdf_without_text_layer_is_rejected():
    data = _pdf_without_text()
    with pytest.raises(ImportParseError) as excinfo:
        import_pdf.parse_pdf(data)
    assert str(excinfo.value) == "pdf_no_text_layer"


@requires_sandbox
def test_corrupted_pdf_is_rejected_as_unreadable():
    with pytest.raises(ImportParseError) as excinfo:
        import_pdf.parse_pdf(b"this is not a pdf at all")
    assert str(excinfo.value) == "pdf_unreadable"


# ---------------------------------------------------------------------------
# Ende-zu-Ende über die bestehende API (Upload -> Vorschau -> complete)
# ---------------------------------------------------------------------------


@requires_sandbox
def test_upload_preview_and_complete_pdf_statement_end_to_end(client, owner_headers):
    _create_household(client, owner_headers)
    account = _create_account(client, owner_headers, opening_balance=0)
    category = _expense_category(client, owner_headers)
    income_category = next(
        item
        for item in client.get(f"{PREFIX}/categories", headers=owner_headers).json()
        if item["kind"] == "income"
    )

    data = _pdf_with_text(_STATEMENT_LINES)
    uploaded = client.post(
        f"{PREFIX}/imports",
        headers=owner_headers,
        data={"account_id": str(account["id"]), "format": "pdf"},
        files={"file": ("auszug.pdf", data, "application/pdf")},
    )
    assert uploaded.status_code == 201, uploaded.text
    batch = uploaded.json()
    assert batch["source_format"] == "pdf"
    assert len(batch["rows"]) == 3

    expense_row = next(row for row in batch["rows"] if row["amount_minor"] == -85000)
    income_row = next(row for row in batch["rows"] if row["amount_minor"] == 250000)
    ambiguous_row = next(row for row in batch["rows"] if row["status"] == "error")
    assert ambiguous_row["errors"] == ["pdf_line_ambiguous"]

    for row, cat in ((expense_row, category), (income_row, income_category)):
        patched = client.patch(
            f"{PREFIX}/imports/{batch['id']}/rows/{row['id']}",
            headers=owner_headers,
            json={"revision": row["revision"], "status": "accepted", "category_id": cat["id"]},
        )
        assert patched.status_code == 200, patched.text

    completed = client.post(
        f"{PREFIX}/imports/{batch['id']}/complete",
        headers=owner_headers,
        json={"revision": batch["revision"]},
    )
    assert completed.status_code == 200, completed.text
    imported_rows = [row for row in completed.json()["rows"] if row["status"] == "imported"]
    assert len(imported_rows) == 2
    for row in imported_rows:
        transaction = client.get(
            f"{PREFIX}/transactions/{row['transaction_id']}", headers=owner_headers
        ).json()
        assert sum(posting["base_amount"] for posting in transaction["postings"]) == 0


@requires_sandbox
def test_scan_pdf_upload_returns_422_with_contract_error_code(client, owner_headers):
    _create_household(client, owner_headers)
    account = _create_account(client, owner_headers, opening_balance=0)
    response = client.post(
        f"{PREFIX}/imports",
        headers=owner_headers,
        data={"account_id": str(account["id"]), "format": "pdf"},
        files={"file": ("scan.pdf", _pdf_without_text(), "application/pdf")},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "pdf_no_text_layer"


@requires_sandbox
def test_pdf_auto_detection_from_file_signature(client, owner_headers):
    _create_household(client, owner_headers)
    account = _create_account(client, owner_headers, opening_balance=0)
    response = client.post(
        f"{PREFIX}/imports",
        headers=owner_headers,
        data={"account_id": str(account["id"]), "format": "auto"},
        files={"file": ("auszug.pdf", _pdf_with_text(_STATEMENT_LINES), "application/pdf")},
    )
    assert response.status_code == 201, response.text
    assert response.json()["source_format"] == "pdf"
