"""Visibility-scoped read model and metrics for imported PAYBACK data."""

from __future__ import annotations

import sqlite3

from hydrahive.api.middleware.auth import AuthPrincipal
from hydrahive.db.connection import db

from .access import membership, require_row
from .common import as_dict
from .loyalty_connections import _connection_dict

BALANCE_HISTORY_LIMIT = 50
ACTIVITY_LIMIT = 200
COUPON_LIMIT = 200
EXPIRATION_LIMIT = 100
PARTNER_LIMIT = 500


def _visible_connection(
    conn: sqlite3.Connection, connection_id: int, member: sqlite3.Row
) -> sqlite3.Row:
    row = conn.execute(
        "SELECT * FROM module_haushaltsbuch_loyalty_connections "
        "WHERE id=? AND household_id=? AND provider='payback'",
        (connection_id, member["household_id"]),
    ).fetchone()
    if row is None:
        return require_row(None, "loyalty_connection_not_found")
    visible = (
        member["role"] == "owner"
        or row["owner_member_id"] == member["id"]
        or row["visibility"] == "household"
    )
    return row if visible else require_row(None, "loyalty_connection_not_found")


def _rows(rows) -> list[dict]:
    return [as_dict(row) for row in rows]


def connection_data(connection_id: int, principal: AuthPrincipal) -> dict:
    with db() as conn:
        member = membership(conn, principal)
        connection = _visible_connection(conn, connection_id, member)
        balances = conn.execute(
            "SELECT id,observed_at,available_points,money_value_minor,"
            "money_value_currency,valuation_version,created_at "
            "FROM module_haushaltsbuch_loyalty_balances WHERE connection_id=? "
            "ORDER BY observed_at DESC,id DESC LIMIT ?",
            (connection_id, BALANCE_HISTORY_LIMIT),
        ).fetchall()
        expirations = conn.execute(
            "SELECT id,expiration_date,points,status,provider_updated_at,first_seen_at,"
            "last_seen_at FROM module_haushaltsbuch_loyalty_expirations "
            "WHERE connection_id=? ORDER BY expiration_date,id LIMIT ?",
            (connection_id, EXPIRATION_LIMIT),
        ).fetchall()
        activities = conn.execute(
            "SELECT a.id,a.provider_activity_id,a.activity_type,a.activity_date,"
            "a.points_delta,a.partner_id,p.name AS partner_name,a.original_description,"
            "a.purchase_amount_minor,a.purchase_currency,a.provider_updated_at,"
            "a.first_seen_at,a.last_seen_at,a.remote_status "
            "FROM module_haushaltsbuch_loyalty_activities a "
            "LEFT JOIN module_haushaltsbuch_loyalty_partners p ON p.id=a.partner_id "
            "WHERE a.connection_id=? ORDER BY a.activity_date DESC,a.id DESC LIMIT ?",
            (connection_id, ACTIVITY_LIMIT),
        ).fetchall()
        coupons = conn.execute(
            "SELECT c.id,c.provider_coupon_id,c.partner_id,p.name AS partner_name,c.title,"
            "c.description,c.valid_from,c.valid_until,c.activation_status,c.multiplier,"
            "c.bonus_points,c.condition_text,c.first_seen_at,c.last_seen_at,"
            "c.provider_updated_at,c.remote_status "
            "FROM module_haushaltsbuch_loyalty_coupons c "
            "LEFT JOIN module_haushaltsbuch_loyalty_partners p ON p.id=c.partner_id "
            "WHERE c.connection_id=? ORDER BY c.valid_until DESC,c.id DESC LIMIT ?",
            (connection_id, COUPON_LIMIT),
        ).fetchall()
        partners = conn.execute(
            "SELECT p.id,p.provider_partner_id,p.name,p.active,p.first_seen_at,p.last_seen_at "
            "FROM module_haushaltsbuch_loyalty_partners p WHERE p.household_id=? "
            "AND p.provider='payback' AND ("
            "EXISTS(SELECT 1 FROM module_haushaltsbuch_loyalty_activities a "
            "WHERE a.connection_id=? AND a.partner_id=p.id) OR "
            "EXISTS(SELECT 1 FROM module_haushaltsbuch_loyalty_coupons c "
            "WHERE c.connection_id=? AND c.partner_id=p.id)) "
            "ORDER BY p.name,p.id LIMIT ?",
            (member["household_id"], connection_id, connection_id, PARTNER_LIMIT),
        ).fetchall()
        metrics = _metrics(conn, connection_id)
    balance_data = _rows(balances)
    return {
        "connection": _connection_dict(connection),
        "latest_balance": balance_data[0] if balance_data else None,
        "balance_history": balance_data,
        "expirations": _rows(expirations),
        "activities": _rows(activities),
        "coupons": _rows(coupons),
        "partners": _rows(partners),
        "metrics": metrics,
        "limits": {
            "balance_history": BALANCE_HISTORY_LIMIT,
            "expirations": EXPIRATION_LIMIT,
            "activities": ACTIVITY_LIMIT,
            "coupons": COUPON_LIMIT,
            "partners": PARTNER_LIMIT,
        },
    }


def _metrics(conn: sqlite3.Connection, connection_id: int) -> dict:
    activity = conn.execute(
        "SELECT COUNT(*) AS activity_count,"
        "COALESCE(SUM(CASE WHEN activity_type='earn' AND points_delta>0 "
        "THEN points_delta ELSE 0 END),0) AS points_collected,"
        "COALESCE(SUM(CASE WHEN activity_type='redeem' AND points_delta<0 "
        "THEN -points_delta ELSE 0 END),0) AS points_redeemed "
        "FROM module_haushaltsbuch_loyalty_activities "
        "WHERE connection_id=? AND remote_status='active'",
        (connection_id,),
    ).fetchone()
    partner_frequency = _rows(
        conn.execute(
            "SELECT p.id AS partner_id,p.name,COUNT(*) AS activity_count "
            "FROM module_haushaltsbuch_loyalty_activities a "
            "JOIN module_haushaltsbuch_loyalty_partners p ON p.id=a.partner_id "
            "WHERE a.connection_id=? AND a.remote_status='active' "
            "GROUP BY p.id,p.name ORDER BY activity_count DESC,p.name LIMIT ?",
            (connection_id, PARTNER_LIMIT),
        ).fetchall()
    )
    purchase_totals = _rows(
        conn.execute(
            "SELECT purchase_currency AS currency,SUM(purchase_amount_minor) AS amount_minor,"
            "COUNT(*) AS activity_count FROM module_haushaltsbuch_loyalty_activities "
            "WHERE connection_id=? AND remote_status='active' "
            "AND purchase_amount_minor IS NOT NULL AND purchase_currency IS NOT NULL "
            "GROUP BY purchase_currency ORDER BY purchase_currency",
            (connection_id,),
        ).fetchall()
    )
    coupon_status = {
        row["activation_status"]: row["count"]
        for row in conn.execute(
            "SELECT activation_status,COUNT(*) AS count "
            "FROM module_haushaltsbuch_loyalty_coupons "
            "WHERE connection_id=? AND remote_status='active' GROUP BY activation_status",
            (connection_id,),
        ).fetchall()
    }
    return {
        "activity_count": activity["activity_count"],
        "points_collected": activity["points_collected"],
        "points_redeemed": activity["points_redeemed"],
        "partner_frequency": partner_frequency,
        "purchase_totals": purchase_totals,
        "coupon_status": coupon_status,
    }
