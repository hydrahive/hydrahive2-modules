"""Idempotente Persistenz normalisierter Loyalty-Providerdaten."""
from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass, field

from .loyalty_receipt_models import ProviderReceipt
from .loyalty_provider import (
    ProviderActivity,
    ProviderBalance,
    ProviderCoupon,
    ProviderExpiration,
    ProviderPartner,
)


@dataclass(slots=True)
class SyncPayload:
    balance: ProviderBalance | None = None
    expirations: list[ProviderExpiration] = field(default_factory=list)
    partners: list[ProviderPartner] = field(default_factory=list)
    activities: list[ProviderActivity] = field(default_factory=list)
    coupons: list[ProviderCoupon] = field(default_factory=list)
    receipts: list[ProviderReceipt] = field(default_factory=list)


@dataclass(slots=True)
class SyncCounts:
    fetched: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0


def _iso(value) -> str | None:
    return value.isoformat() if value is not None else None


def _balance_fingerprint(item: ProviderBalance) -> str:
    raw = "|".join(
        str(value) for value in (
            _iso(item.observed_at), item.points, item.money_value_minor,
            item.money_value_currency, item.valuation_version,
        )
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def _upsert_partners(conn, household_id, provider, items, counts) -> dict[str, int]:
    result: dict[str, int] = {}
    for item in items:
        row = conn.execute(
            "SELECT id,name,active FROM module_haushaltsbuch_loyalty_partners "
            "WHERE household_id=? AND provider=? AND provider_partner_id=?",
            (household_id, provider, item.provider_id),
        ).fetchone()
        if row is None:
            cursor = conn.execute(
                "INSERT INTO module_haushaltsbuch_loyalty_partners"
                "(household_id,provider,provider_partner_id,name,active) VALUES(?,?,?,?,?)",
                (household_id, provider, item.provider_id, item.name, int(item.active)),
            )
            result[item.provider_id] = cursor.lastrowid
            counts.created += 1
        else:
            result[item.provider_id] = row["id"]
            if row["name"] != item.name or bool(row["active"]) != item.active:
                conn.execute(
                    "UPDATE module_haushaltsbuch_loyalty_partners "
                    "SET name=?,active=?,last_seen_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') "
                    "WHERE id=?",
                    (item.name, int(item.active), row["id"]),
                )
                counts.updated += 1
            else:
                counts.skipped += 1
    return result


def persist_sync(
    conn: sqlite3.Connection, connection: sqlite3.Row, payload: SyncPayload
) -> SyncCounts:
    counts = SyncCounts()
    household_id, connection_id = connection["household_id"], connection["id"]
    counts.fetched = sum((
        int(payload.balance is not None), len(payload.expirations),
        len(payload.partners), len(payload.activities), len(payload.coupons),
    ))
    partner_ids = _upsert_partners(
        conn, household_id, connection["provider"], payload.partners, counts
    )
    if payload.balance is not None:
        item = payload.balance
        cursor = conn.execute(
            "INSERT OR IGNORE INTO module_haushaltsbuch_loyalty_balances"
            "(household_id,connection_id,observed_at,available_points,money_value_minor,"
            "money_value_currency,valuation_version,fingerprint) VALUES(?,?,?,?,?,?,?,?)",
            (
                household_id, connection_id, _iso(item.observed_at), item.points,
                item.money_value_minor, item.money_value_currency,
                item.valuation_version, _balance_fingerprint(item),
            ),
        )
        counts.created += cursor.rowcount
        counts.skipped += int(not cursor.rowcount)
    for item in payload.expirations:
        existing = conn.execute(
            "SELECT id FROM module_haushaltsbuch_loyalty_expirations "
            "WHERE connection_id=? AND expiration_date=?",
            (connection_id, _iso(item.expires_on)),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE module_haushaltsbuch_loyalty_expirations "
                "SET points=?,status=?,last_seen_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=?",
                (item.points, item.status, existing["id"]),
            )
            counts.updated += 1
        else:
            conn.execute(
                "INSERT INTO module_haushaltsbuch_loyalty_expirations"
                "(household_id,connection_id,expiration_date,points,status) VALUES(?,?,?,?,?)",
                (household_id, connection_id, _iso(item.expires_on), item.points, item.status),
            )
            counts.created += 1
    _upsert_activities(conn, connection, payload.activities, partner_ids, counts)
    _upsert_coupons(conn, connection, payload.coupons, partner_ids, counts)
    return counts


def _upsert_activities(conn, connection, items, partner_ids, counts) -> None:
    for item in items:
        partner_id = partner_ids.get(item.partner_provider_id or "")
        existing = conn.execute(
            "SELECT id FROM module_haushaltsbuch_loyalty_activities "
            "WHERE connection_id=? AND (fingerprint=? OR "
            "(provider_activity_id=? AND ? IS NOT NULL))",
            (connection["id"], item.fingerprint, item.provider_id, item.provider_id),
        ).fetchone()
        values = (
            item.provider_id, item.fingerprint, item.kind, _iso(item.occurred_on),
            item.points_delta, partner_id, item.description, item.purchase_amount_minor,
            item.purchase_currency, _iso(item.provider_updated_at),
        )
        if existing:
            conn.execute(
                "UPDATE module_haushaltsbuch_loyalty_activities SET "
                "provider_activity_id=?,fingerprint=?,activity_type=?,activity_date=?,"
                "points_delta=?,partner_id=?,original_description=?,purchase_amount_minor=?,"
                "purchase_currency=?,provider_updated_at=?,"
                "last_seen_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=?",
                (*values, existing["id"]),
            )
            counts.updated += 1
        else:
            conn.execute(
                "INSERT INTO module_haushaltsbuch_loyalty_activities"
                "(household_id,connection_id,provider_activity_id,fingerprint,activity_type,"
                "activity_date,points_delta,partner_id,original_description,"
                "purchase_amount_minor,purchase_currency,provider_updated_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (connection["household_id"], connection["id"], *values),
            )
            counts.created += 1


def _upsert_coupons(conn, connection, items, partner_ids, counts) -> None:
    for item in items:
        partner_id = partner_ids.get(item.partner_provider_id or "")
        existing = conn.execute(
            "SELECT id FROM module_haushaltsbuch_loyalty_coupons "
            "WHERE connection_id=? AND (fingerprint=? OR "
            "(provider_coupon_id=? AND ? IS NOT NULL))",
            (connection["id"], item.fingerprint, item.provider_id, item.provider_id),
        ).fetchone()
        values = (
            item.provider_id, item.fingerprint, partner_id, item.title, item.description,
            _iso(item.valid_from), _iso(item.valid_until), item.status,
            item.multiplier, item.bonus_points, item.condition_text,
            _iso(item.provider_updated_at),
        )
        if existing:
            conn.execute(
                "UPDATE module_haushaltsbuch_loyalty_coupons SET provider_coupon_id=?,"
                "fingerprint=?,partner_id=?,title=?,description=?,valid_from=?,valid_until=?,"
                "activation_status=?,multiplier=?,bonus_points=?,condition_text=?,"
                "provider_updated_at=?,last_seen_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') "
                "WHERE id=?",
                (*values, existing["id"]),
            )
            counts.updated += 1
        else:
            conn.execute(
                "INSERT INTO module_haushaltsbuch_loyalty_coupons"
                "(household_id,connection_id,provider_coupon_id,fingerprint,partner_id,title,"
                "description,valid_from,valid_until,activation_status,multiplier,bonus_points,"
                "condition_text,provider_updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (connection["household_id"], connection["id"], *values),
            )
            counts.created += 1
