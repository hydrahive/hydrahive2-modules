from __future__ import annotations

import hashlib
import json
import sqlite3

from fastapi import status

from hydrahive.api.middleware.auth import AuthPrincipal
from hydrahive.api.middleware.errors import coded
from hydrahive.db.connection import db

from . import audit
from .access import membership, require_row
from .import_parsers import (
    CsvMapping,
    ImportParseError,
    detect_format,
    parse_import,
)
from .import_persistence import _batch_dict, _display_filename, _fingerprint, _safe_text

def _csv_mapping(config: dict) -> CsvMapping:
    allowed = set(CsvMapping.__dataclass_fields__)
    try:
        return CsvMapping(**{key: value for key, value in config.items() if key in allowed})
    except (TypeError, ValueError) as exc:
        raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid_csv_mapping") from exc


def create_batch(
    data: bytes,
    filename: str | None,
    account_id: int,
    import_format: str,
    principal: AuthPrincipal,
    *,
    mapping: dict | None = None,
    profile_id: int | None = None,
) -> dict:
    with db(immediate=True) as conn:
        member = membership(conn, principal)
        account = require_row(conn.execute(
            "SELECT a.*,h.base_currency FROM module_haushaltsbuch_accounts a "
            "JOIN module_haushaltsbuch_households h ON h.id=a.household_id "
            "WHERE a.id=? AND a.household_id=? AND a.archived=0",
            (account_id, member["household_id"]),
        ).fetchone(), "account_not_found")
        if account["currency"] != account["base_currency"]:
            raise coded(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "import_base_currency_account_required",
            )
        selected = detect_format(data, filename or "") if import_format == "auto" else import_format.lower()
        csv_config = mapping
        if profile_id is not None:
            profile = require_row(conn.execute(
                "SELECT * FROM module_haushaltsbuch_import_profiles WHERE id=? AND household_id=?",
                (profile_id, member["household_id"]),
            ).fetchone(), "import_profile_not_found")
            profile_config = {
                **json.loads(profile["mapping_json"]),
                "delimiter": profile["delimiter"],
                "encoding": profile["encoding"],
                "decimal_separator": profile["decimal_separator"],
                "date_format": profile["date_format"],
            }
            csv_config = {**profile_config, **(mapping or {})}
        if csv_config is not None:
            csv_config = {**csv_config, "default_currency": account["currency"]}
        csv_mapping = _csv_mapping(csv_config) if selected == "csv" and csv_config else None
        try:
            records = parse_import(data, selected, csv_mapping, filename=filename or "")
        except ImportParseError as exc:
            raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        file_hash = hashlib.sha256(data).hexdigest()
        if conn.execute(
            "SELECT 1 FROM module_haushaltsbuch_import_batches WHERE household_id=? AND file_hash=?",
            (member["household_id"], file_hash),
        ).fetchone():
            raise coded(status.HTTP_409_CONFLICT, "duplicate_import_file")
        try:
            cursor = conn.execute(
                "INSERT INTO module_haushaltsbuch_import_batches"
                "(household_id,account_id,profile_id,display_filename,source_format,file_hash,created_by) VALUES(?,?,?,?,?,?,?)",
                (member["household_id"], account_id, profile_id, _display_filename(filename), selected, file_hash, principal.user_id),
            )
        except sqlite3.IntegrityError as exc:
            raise coded(status.HTTP_409_CONFLICT, "duplicate_import_file") from exc
        batch_id = int(cursor.lastrowid)
        for record in records:
            fingerprint, strength = _fingerprint(account_id, record)
            duplicate = conn.execute(
                "SELECT 1 FROM module_haushaltsbuch_import_rows WHERE household_id=? AND fingerprint=?",
                (member["household_id"], fingerprint),
            ).fetchone()
            warnings = list(record.warnings)
            errors = list(record.errors)
            row_status = "error" if errors else "pending"
            if not errors and duplicate and strength == "strong":
                row_status = "duplicate"
            elif not errors and duplicate:
                warnings.append("possible_duplicate")
            if record.currency is not None and record.currency != account["currency"]:
                errors.append("account_currency_mismatch")
                row_status = "error"
            conn.execute(
                "INSERT INTO module_haushaltsbuch_import_rows"
                "(household_id,batch_id,source_line,booking_date,value_date,amount_minor,currency,counterparty,purpose,counterparty_identifier,bank_reference,category_hint,warnings_json,errors_json,fingerprint,fingerprint_strength,status) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (member["household_id"], batch_id, record.source_line,
                 record.booking_date.isoformat() if record.booking_date else None,
                 record.value_date.isoformat() if record.value_date else None,
                 record.amount_minor, record.currency,
                 _safe_text(record.counterparty, 240), _safe_text(record.purpose, 500),
                 _safe_text(record.counterparty_identifier, 32), _safe_text(record.bank_reference, 240),
                 _safe_text(record.category_hint, 120), json.dumps(warnings), json.dumps(errors), fingerprint, strength, row_status),
            )
        batch = conn.execute("SELECT * FROM module_haushaltsbuch_import_batches WHERE id=?", (batch_id,)).fetchone()
        audit.record(conn, member["household_id"], principal.user_id, "import_batch", batch_id, "create", after={"filename": batch["display_filename"], "format": selected, "record_count": len(records)})
        result = _batch_dict(conn, batch, True)
    return result


def list_batches(principal: AuthPrincipal) -> list[dict]:
    with db() as conn:
        member = membership(conn, principal)
        rows = conn.execute(
            "SELECT * FROM module_haushaltsbuch_import_batches WHERE household_id=? ORDER BY id DESC",
            (member["household_id"],),
        ).fetchall()
        return [_batch_dict(conn, row) for row in rows]


def get_batch(batch_id: int, principal: AuthPrincipal) -> dict:
    with db() as conn:
        member = membership(conn, principal)
        row = require_row(conn.execute(
            "SELECT * FROM module_haushaltsbuch_import_batches WHERE id=? AND household_id=?",
            (batch_id, member["household_id"]),
        ).fetchone(), "import_batch_not_found")
        return _batch_dict(conn, row, True)
