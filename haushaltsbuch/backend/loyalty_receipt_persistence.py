"""Idempotente Persistenz kanonischer Belege ohne Rohpayloads."""
from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3

from hydrahive.settings import settings

from .loyalty_persistence import SyncCounts
from .loyalty_receipt_models import ProviderReceipt

_NOW = "strftime('%Y-%m-%dT%H:%M:%fZ','now')"


def _fingerprint(household_id: int, provider_id: str) -> str:
    message = f"{household_id}|lidl_plus|{provider_id}".encode()
    return hmac.new(settings.secret_key.encode(), message, hashlib.sha256).hexdigest()


def _insert_children(
    conn: sqlite3.Connection, household_id: int, receipt_id: int,
    receipt: ProviderReceipt,
) -> None:
    item_ids: dict[int, int] = {}
    for item in receipt.items:
        cursor = conn.execute(
            "INSERT INTO module_haushaltsbuch_loyalty_receipt_items"
            "(household_id,receipt_id,sequence,original_name,gtin,quantity,unit,"
            "unit_price_minor,total_minor,tax_group,is_return) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (
                household_id, receipt_id, item.sequence, item.original_name, item.gtin,
                item.quantity, item.unit, item.unit_price_minor, item.total_minor,
                item.tax_group, int(item.is_return),
            ),
        )
        item_ids[item.sequence] = cursor.lastrowid
    for adjustment in receipt.adjustments:
        conn.execute(
            "INSERT INTO module_haushaltsbuch_loyalty_receipt_adjustments"
            "(household_id,receipt_id,item_id,kind,amount_minor,description) "
            "VALUES(?,?,?,?,?,?)",
            (
                household_id, receipt_id, item_ids.get(adjustment.item_sequence),
                adjustment.kind, adjustment.amount_minor, adjustment.description,
            ),
        )


def _values(household_id: int, connection_id: int, receipt: ProviderReceipt) -> tuple:
    return (
        household_id, connection_id, receipt.provider_id,
        _fingerprint(household_id, receipt.provider_id), receipt.merchant_name,
        receipt.store_id, receipt.store_name, receipt.store_address,
        receipt.purchased_at.isoformat() if receipt.purchased_at else None,
        receipt.total_minor, receipt.currency, receipt.total_discount_minor,
        receipt.content_hash, receipt.validation_status,
        json.dumps(receipt.warnings, ensure_ascii=False),
    )


def _create(
    conn: sqlite3.Connection, household_id: int, connection_id: int,
    receipt: ProviderReceipt,
) -> None:
    cursor = conn.execute(
        "INSERT INTO module_haushaltsbuch_loyalty_receipts"
        "(household_id,connection_id,provider_receipt_id,provider_fingerprint,"
        "merchant_name,store_id,store_name,store_address,purchased_at,total_minor,"
        "currency,total_discount_minor,content_hash,validation_status,warnings_json) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        _values(household_id, connection_id, receipt),
    )
    _insert_children(conn, household_id, cursor.lastrowid, receipt)


def _update(
    conn: sqlite3.Connection, existing: sqlite3.Row, household_id: int,
    connection_id: int, receipt: ProviderReceipt,
) -> None:
    values = _values(household_id, connection_id, receipt)
    conn.execute(
        f"UPDATE module_haushaltsbuch_loyalty_receipts SET household_id=?,"
        "connection_id=?,provider_receipt_id=?,provider_fingerprint=?,merchant_name=?,"
        "store_id=?,store_name=?,store_address=?,purchased_at=?,total_minor=?,currency=?,"
        "total_discount_minor=?,content_hash=?,validation_status=?,warnings_json=?,"
        f"last_seen_at={_NOW} WHERE id=?",
        (*values, existing["id"]),
    )
    conn.execute(
        "DELETE FROM module_haushaltsbuch_loyalty_receipt_adjustments WHERE receipt_id=?",
        (existing["id"],),
    )
    conn.execute(
        "DELETE FROM module_haushaltsbuch_loyalty_receipt_items WHERE receipt_id=?",
        (existing["id"],),
    )
    _insert_children(conn, household_id, existing["id"], receipt)


def persist_receipts(
    conn: sqlite3.Connection, connection: sqlite3.Row,
    receipts: list[ProviderReceipt],
) -> SyncCounts:
    counts = SyncCounts(fetched=len(receipts))
    household_id, connection_id = connection["household_id"], connection["id"]
    for receipt in receipts:
        existing = conn.execute(
            "SELECT id,content_hash FROM module_haushaltsbuch_loyalty_receipts "
            "WHERE connection_id=? AND provider_receipt_id=?",
            (connection_id, receipt.provider_id),
        ).fetchone()
        if existing is None:
            _create(conn, household_id, connection_id, receipt)
            counts.created += 1
        elif existing["content_hash"] != receipt.content_hash:
            _update(conn, existing, household_id, connection_id, receipt)
            counts.updated += 1
        else:
            conn.execute(
                f"UPDATE module_haushaltsbuch_loyalty_receipts SET last_seen_at={_NOW} "
                "WHERE id=?", (existing["id"],),
            )
            counts.skipped += 1
    return counts
