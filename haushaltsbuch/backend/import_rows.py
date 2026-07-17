from __future__ import annotations

import json
from datetime import date

from fastapi import status

from hydrahive.api.middleware.auth import AuthPrincipal
from hydrahive.api.middleware.errors import coded
from hydrahive.db.connection import db

from . import audit
from .access import conflict, membership, require_row
from .common import NOW
from .import_models import ImportRowUpdate
from .import_parsers import NormalizedRecord
from .import_persistence import _fingerprint, _row_dict, _safe_text

_IMMUTABLE_PARSER_ERRORS = {"camt_batch_amount_mismatch"}

_EDITABLE = (
    "status",
    "category_id",
    "booking_date",
    "value_date",
    "amount_minor",
    "currency",
    "counterparty",
    "purpose",
)


def _apply_patch(values: dict, body: ImportRowUpdate) -> None:
    for field in _EDITABLE:
        if field not in body.model_fields_set:
            continue
        value = getattr(body, field)
        values[field] = value.isoformat() if hasattr(value, "isoformat") else value


def _validate_core(values: dict, account_currency: str) -> list[str]:
    errors: list[str] = []
    if values["booking_date"] is None:
        errors.append("invalid_date")
    if values["amount_minor"] is None or values["amount_minor"] == 0:
        errors.append("invalid_amount")
    if values["currency"] is None:
        errors.append("invalid_currency")
    elif values["currency"] != account_currency:
        errors.append("account_currency_mismatch")
    return errors


def _record(values: dict, errors: list[str]) -> NormalizedRecord:
    return NormalizedRecord(
        source_line=values["source_line"],
        booking_date=date.fromisoformat(values["booking_date"])
        if values["booking_date"]
        else None,
        value_date=date.fromisoformat(values["value_date"])
        if values["value_date"]
        else None,
        amount_minor=values["amount_minor"],
        currency=values["currency"],
        counterparty=values["counterparty"],
        purpose=values["purpose"],
        bank_reference=values["bank_reference"],
        errors=tuple(errors),
    )


def update_row(
    batch_id: int,
    row_id: int,
    body: ImportRowUpdate,
    principal: AuthPrincipal,
) -> dict:
    with db(immediate=True) as conn:
        member = membership(conn, principal)
        batch = require_row(
            conn.execute(
                "SELECT b.*,a.currency account_currency "
                "FROM module_haushaltsbuch_import_batches b "
                "JOIN module_haushaltsbuch_accounts a ON a.id=b.account_id "
                "WHERE b.id=? AND b.household_id=?",
                (batch_id, member["household_id"]),
            ).fetchone(),
            "import_batch_not_found",
        )
        if batch["status"] != "draft":
            conflict("import_batch_not_draft")
        before = require_row(
            conn.execute(
                "SELECT * FROM module_haushaltsbuch_import_rows "
                "WHERE id=? AND batch_id=? AND household_id=?",
                (row_id, batch_id, member["household_id"]),
            ).fetchone(),
            "import_row_not_found",
        )
        values = dict(before)
        _apply_patch(values, body)
        immutable_errors = [
            item
            for item in json.loads(before["errors_json"])
            if item in _IMMUTABLE_PARSER_ERRORS
        ]
        errors = [*immutable_errors, *_validate_core(values, batch["account_currency"])]
        if not errors and before["status"] == "error" and "status" not in body.model_fields_set:
            values["status"] = "pending"
        if values["status"] == "accepted" and errors:
            raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "import_row_has_errors")
        if values["category_id"] is not None:
            require_row(
                conn.execute(
                    "SELECT 1 FROM module_haushaltsbuch_categories "
                    "WHERE id=? AND household_id=? AND archived=0",
                    (values["category_id"], member["household_id"]),
                ).fetchone(),
                "category_not_found",
            )

        fingerprint, strength = _fingerprint(
            batch["account_id"], _record(values, errors)
        )
        duplicate = conn.execute(
            "SELECT 1 FROM module_haushaltsbuch_import_rows "
            "WHERE household_id=? AND fingerprint=? AND id<>?",
            (member["household_id"], fingerprint, row_id),
        ).fetchone()
        warnings = [
            item
            for item in json.loads(values["warnings_json"])
            if item != "possible_duplicate"
        ]
        if duplicate and strength == "strong" and values["status"] == "accepted":
            raise coded(status.HTTP_409_CONFLICT, "duplicate_import_row")
        if duplicate and strength == "weak" and not errors:
            warnings.append("possible_duplicate")

        cursor = conn.execute(
            f"UPDATE module_haushaltsbuch_import_rows SET status=?,category_id=?,"
            f"booking_date=?,value_date=?,amount_minor=?,currency=?,counterparty=?,"
            f"purpose=?,warnings_json=?,errors_json=?,fingerprint=?,fingerprint_strength=?,"
            f"revision=revision+1,updated_at={NOW} "
            "WHERE id=? AND household_id=? AND revision=?",
            (
                values["status"], values["category_id"], values["booking_date"],
                values["value_date"], values["amount_minor"], values["currency"],
                _safe_text(values["counterparty"], 240),
                _safe_text(values["purpose"], 500), json.dumps(warnings),
                json.dumps(errors), fingerprint, strength, row_id,
                member["household_id"], body.revision,
            ),
        )
        if not cursor.rowcount:
            conflict()
        row = conn.execute(
            "SELECT * FROM module_haushaltsbuch_import_rows WHERE id=?", (row_id,)
        ).fetchone()
        audit.record(
            conn, member["household_id"], principal.user_id, "import_row", row_id,
            "update", {"status": before["status"]}, {"status": row["status"]},
        )
    return _row_dict(row)
