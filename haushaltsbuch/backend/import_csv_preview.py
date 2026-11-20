"""POST /imports/csv-preview (Vertrag hb-bank-csv-notes.md): zeigt die
erkannten Spalten einer CSV-Datei, OHNE etwas zu schreiben - für den
Zuordnungsdialog bei unbekannten Bank-Kopfzeilen (Vorbelegung) UND um auch
bei einer bekannten Bank schon vor dem eigentlichen Import zu sehen, was
erkannt wurde.

Ownership/Größenlimit wie POST /imports (validate_upload_target), aber kein
DB-Write - reine Lese-/Analysefunktion über die Bytes des Uploads.
"""

from __future__ import annotations

import csv

from hydrahive.api.middleware.auth import AuthPrincipal

from .import_bank_csv_rewrite import detect_bank_template
from .import_csv import detect_encoding
from .import_parsers import ImportParseError, check_file_size
from .import_persistence import validate_upload_target

_SAMPLE_ROWS = 5
_DELIMITERS = (";", ",", "\t")


def _guess_delimiter(line: str) -> str:
    """Trennzeichen mit den meisten Vorkommen in der Kopfzeile - ";" ist der
    Standard bei deutschen Bank-CSVs, daher zuerst geprüft (gleichstand zählt
    als ";")."""
    counts = {delimiter: line.count(delimiter) for delimiter in _DELIMITERS}
    best = max(counts, key=lambda delimiter: counts[delimiter])
    return best if counts[best] > 0 else ";"


def preview_csv(account_id: int, data: bytes, principal: AuthPrincipal) -> dict:
    """{encoding, delimiter, header, header_line, bank, sample_rows} - schreibt
    nichts. Ownership/Größenlimit wie POST /imports."""
    validate_upload_target(account_id, principal)
    check_file_size(data)
    try:
        encoding = detect_encoding(data)
    except ImportParseError as exc:
        from fastapi import status
        from hydrahive.api.middleware.errors import coded

        raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    text = data.decode(encoding)
    detected = detect_bank_template(data)
    bank = None
    header_line = 0
    delimiter = ";"
    if detected is not None:
        template, _detected_encoding, header_line = detected
        bank = {"id": template.id, "label": template.label}
    else:
        lines = text.splitlines()
        for idx, line in enumerate(lines[:20]):
            if line.strip():
                delimiter = _guess_delimiter(line)
                header_line = idx
                break
    lines = text.splitlines()[header_line:]
    rows = list(csv.reader(lines, delimiter=delimiter))
    header = rows[0] if rows else []
    sample_rows = rows[1 : 1 + _SAMPLE_ROWS]
    return {
        "encoding": encoding, "delimiter": delimiter, "header": header,
        "header_line": header_line, "bank": bank, "sample_rows": sample_rows,
    }
