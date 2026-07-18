from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from pathlib import PurePath

from fastapi import status

from hydrahive.api.middleware.auth import AuthPrincipal
from hydrahive.api.middleware.errors import coded
from hydrahive.db.connection import db

from . import audit
from .access import conflict, membership, require_row
from .common import NOW, as_dict
from .import_models import ImportProfileCreate, ImportProfileUpdate
from .import_parsers import NormalizedRecord, normalize_bank_reference

_IBAN = re.compile(r"(?<![A-Z0-9])([A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]){11,30})(?![A-Z0-9])", re.IGNORECASE)
_BIC = re.compile(r"(?<![A-Z0-9])([A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?)(?![A-Z0-9])")


def _safe_text(value: str | None, maximum: int) -> str | None:
    if not value:
        return None
    value = " ".join(value.split())

    def mask(match: re.Match) -> str:
        compact = match.group(1).replace(" ", "")
        return f"****{compact[-4:]}"

    return _BIC.sub(mask, _IBAN.sub(mask, value))[:maximum] or None


def _fingerprint(account_id: int, record: NormalizedRecord) -> tuple[str, str]:
    reference = normalize_bank_reference(record.bank_reference)
    if reference and not record.errors:
        source = f"strong|{account_id}|{record.currency}|{reference.casefold()}"
        strength = "strong"
    else:
        parts = [
            "weak", str(account_id),
            record.booking_date.isoformat() if record.booking_date else "",
            str(record.amount_minor) if record.amount_minor is not None else "",
            record.currency or "", (record.counterparty or "").strip().casefold(),
            (record.purpose or "").strip().casefold(),
        ]
        if record.errors:
            parts.extend((str(record.source_line), ",".join(record.errors)))
        source = "|".join(parts)
        strength = "weak"
    return hashlib.sha256(source.encode()).hexdigest(), strength


def _display_filename(filename: str | None) -> str:
    name = PurePath((filename or "import").replace("\\", "/")).name
    name = "".join(char for char in name if char.isprintable() and char not in "/\\")
    return (name[:255] or "import")


def _profile_dict(row: sqlite3.Row) -> dict:
    result = as_dict(row)
    result["mapping"] = json.loads(result.pop("mapping_json"))
    return result


def _row_dict(row: sqlite3.Row) -> dict:
    result = as_dict(row)
    result["warnings"] = json.loads(result.pop("warnings_json"))
    result["errors"] = json.loads(result.pop("errors_json"))
    return result


def _batch_dict(conn: sqlite3.Connection, row: sqlite3.Row, include_rows: bool = False) -> dict:
    result = as_dict(row)
    result.pop("file_hash", None)
    result["rows_revision"] = conn.execute(
        "SELECT COALESCE(SUM(revision),0) "
        "FROM module_haushaltsbuch_import_rows WHERE batch_id=?",
        (row["id"],),
    ).fetchone()[0]
    if include_rows:
        rows = conn.execute(
            "SELECT * FROM module_haushaltsbuch_import_rows WHERE batch_id=? ORDER BY source_line",
            (row["id"],),
        ).fetchall()
        result["rows"] = [_row_dict(item) for item in rows]
    return result


def list_profiles(principal: AuthPrincipal) -> list[dict]:
    with db() as conn:
        member = membership(conn, principal)
        rows = conn.execute(
            "SELECT * FROM module_haushaltsbuch_import_profiles WHERE household_id=? ORDER BY name,id",
            (member["household_id"],),
        ).fetchall()
    return [_profile_dict(row) for row in rows]


def create_profile(body: ImportProfileCreate, principal: AuthPrincipal) -> dict:
    with db(immediate=True) as conn:
        member = membership(conn, principal)
        try:
            cursor = conn.execute(
                "INSERT INTO module_haushaltsbuch_import_profiles"
                "(household_id,name,delimiter,encoding,decimal_separator,date_format,mapping_json) VALUES(?,?,?,?,?,?,?)",
                (
                    member["household_id"], body.name, body.delimiter, body.encoding,
                    body.decimal_separator, body.date_format,
                    json.dumps(body.mapping.model_dump(), ensure_ascii=False, sort_keys=True),
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise coded(status.HTTP_409_CONFLICT, "import_profile_conflict") from exc
        row = conn.execute("SELECT * FROM module_haushaltsbuch_import_profiles WHERE id=?", (cursor.lastrowid,)).fetchone()
        audit.record(conn, member["household_id"], principal.user_id, "import_profile", row["id"], "create", after={"name": row["name"]})
    return _profile_dict(row)


def update_profile(profile_id: int, body: ImportProfileUpdate, principal: AuthPrincipal) -> dict:
    with db(immediate=True) as conn:
        member = membership(conn, principal)
        before = require_row(conn.execute(
            "SELECT * FROM module_haushaltsbuch_import_profiles WHERE id=? AND household_id=?",
            (profile_id, member["household_id"]),
        ).fetchone(), "import_profile_not_found")
        try:
            cursor = conn.execute(
                f"UPDATE module_haushaltsbuch_import_profiles SET name=?,delimiter=?,encoding=?,decimal_separator=?,date_format=?,mapping_json=?,revision=revision+1,updated_at={NOW} WHERE id=? AND household_id=? AND revision=?",
                (body.name, body.delimiter, body.encoding, body.decimal_separator, body.date_format,
                 json.dumps(body.mapping.model_dump(), ensure_ascii=False, sort_keys=True), profile_id,
                 member["household_id"], body.revision),
            )
        except sqlite3.IntegrityError as exc:
            raise coded(status.HTTP_409_CONFLICT, "import_profile_conflict") from exc
        if not cursor.rowcount:
            conflict()
        row = conn.execute("SELECT * FROM module_haushaltsbuch_import_profiles WHERE id=?", (profile_id,)).fetchone()
        audit.record(conn, member["household_id"], principal.user_id, "import_profile", profile_id, "update", {"name": before["name"]}, {"name": row["name"]})
    return _profile_dict(row)


def delete_profile(profile_id: int, revision: int, principal: AuthPrincipal) -> None:
    with db(immediate=True) as conn:
        member = membership(conn, principal)
        row = require_row(conn.execute(
            "SELECT * FROM module_haushaltsbuch_import_profiles WHERE id=? AND household_id=?",
            (profile_id, member["household_id"]),
        ).fetchone(), "import_profile_not_found")
        if row["revision"] != revision:
            conflict()
        try:
            conn.execute("DELETE FROM module_haushaltsbuch_import_profiles WHERE id=?", (profile_id,))
        except sqlite3.IntegrityError as exc:
            raise coded(status.HTTP_409_CONFLICT, "import_profile_in_use") from exc
        audit.record(conn, member["household_id"], principal.user_id, "import_profile", profile_id, "delete", {"name": row["name"]})


def validate_upload_target(account_id: int, principal: AuthPrincipal) -> dict:
    with db() as conn:
        member = membership(conn, principal)
        account = require_row(conn.execute(
            "SELECT a.*,h.base_currency FROM module_haushaltsbuch_accounts a "
            "JOIN module_haushaltsbuch_households h ON h.id=a.household_id "
            "WHERE a.id=? AND a.household_id=?",
            (account_id, member["household_id"]),
        ).fetchone(), "account_not_found")
        if account["archived"]:
            raise coded(status.HTTP_409_CONFLICT, "account_archived")
        if account["currency"] != account["base_currency"]:
            raise coded(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "import_base_currency_account_required",
            )
        return {"household_id": member["household_id"], "currency": account["currency"]}
