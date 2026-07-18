"""Haushaltsgebundene read-only API für normalisierte Providerbelege."""
from __future__ import annotations

import json
import sqlite3

from hydrahive.api.middleware.auth import AuthPrincipal
from hydrahive.db.connection import db

from .access import membership, require_row


def _scope(member: sqlite3.Row) -> tuple[str, tuple]:
    if member["role"] == "owner":
        return "c.household_id=?", (member["household_id"],)
    return (
        "c.household_id=? AND (c.owner_member_id=? OR c.visibility='household')",
        (member["household_id"], member["id"]),
    )


def _receipt_dict(row: sqlite3.Row) -> dict:
    result = dict(row)
    for key in ("household_id", "provider_fingerprint", "content_hash"):
        result.pop(key, None)
    result["warnings"] = json.loads(result.pop("warnings_json"))
    return result


def list_receipts(principal: AuthPrincipal) -> list[dict]:
    with db() as conn:
        member = membership(conn, principal)
        where, params = _scope(member)
        rows = conn.execute(
            "SELECT r.* FROM module_haushaltsbuch_loyalty_receipts r "
            "JOIN module_haushaltsbuch_loyalty_connections c "
            "ON c.id=r.connection_id AND c.household_id=r.household_id "
            f"WHERE {where} ORDER BY r.purchased_at DESC,r.id DESC LIMIT 500",
            params,
        ).fetchall()
    return [_receipt_dict(row) for row in rows]


def receipt_detail(receipt_id: int, principal: AuthPrincipal) -> dict:
    with db() as conn:
        member = membership(conn, principal)
        where, params = _scope(member)
        row = require_row(
            conn.execute(
                "SELECT r.* FROM module_haushaltsbuch_loyalty_receipts r "
                "JOIN module_haushaltsbuch_loyalty_connections c "
                "ON c.id=r.connection_id AND c.household_id=r.household_id "
                f"WHERE r.id=? AND {where}", (receipt_id, *params),
            ).fetchone(),
            "loyalty_receipt_not_found",
        )
        items = conn.execute(
            "SELECT id,sequence,original_name,gtin,quantity,unit,unit_price_minor,"
            "total_minor,tax_group,is_return FROM "
            "module_haushaltsbuch_loyalty_receipt_items "
            "WHERE receipt_id=? AND household_id=? ORDER BY sequence",
            (receipt_id, member["household_id"]),
        ).fetchall()
        adjustments = conn.execute(
            "SELECT id,item_id,kind,amount_minor,description FROM "
            "module_haushaltsbuch_loyalty_receipt_adjustments "
            "WHERE receipt_id=? AND household_id=? ORDER BY id",
            (receipt_id, member["household_id"]),
        ).fetchall()
    result = _receipt_dict(row)
    result["items"] = [{**dict(item), "is_return": bool(item["is_return"])} for item in items]
    result["adjustments"] = [dict(item) for item in adjustments]
    return result
