"""Crypto-Brücke v2 (Etappe A2, VERTRAG-PORT-V2.md): Bestand je Coin + EUR-Wert
je Krypto-Konto, über den Read-Port (wallet_holdings). Snapshot-Rückfall
("stale") analog zu crypto_bridge.get_crypto_value, aber inklusive der
einzelnen Holdings-Positionen statt nur dem Gesamtwert.

Verknüpfung (welche Adressen an welches Konto gebunden sind) lebt in
crypto_addresses.py - diese Datei liest sie nur.
"""

from __future__ import annotations

import json
import sqlite3

from fastapi import status
from hydrahive.api.middleware.auth import AuthPrincipal
from hydrahive.api.middleware.errors import coded
from hydrahive.db.connection import db

from .access import membership
from .crypto_addresses import _own_address_ids
from .crypto_bridge import CryptoBridgeUnavailable, _booked_balance, _load_port, _require_wallet_owned_by


def _store_holdings_snapshot(
    conn: sqlite3.Connection, account_id: int, household_id: int, result: dict
) -> None:
    conn.execute(
        "INSERT INTO module_haushaltsbuch_crypto_holdings_snapshots"
        "(account_id,household_id,value_minor,complete,as_of,holdings_json,addresses_json) "
        "VALUES(?,?,?,?,?,?,?) "
        "ON CONFLICT(account_id) DO UPDATE SET value_minor=excluded.value_minor,"
        "complete=excluded.complete,as_of=excluded.as_of,holdings_json=excluded.holdings_json,"
        "addresses_json=excluded.addresses_json",
        (
            account_id, household_id, result["value_minor"], int(result["complete"]), result["as_of"],
            json.dumps(result["holdings"], ensure_ascii=False),
            json.dumps(result["addresses"], ensure_ascii=False),
        ),
    )


def _load_holdings_snapshot(conn: sqlite3.Connection, account_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM module_haushaltsbuch_crypto_holdings_snapshots WHERE account_id=?", (account_id,)
    ).fetchone()


def _stale_holdings_result(
    account_id: int, snapshot: sqlite3.Row | None, booked_balance: int, reason: str
) -> dict:
    if snapshot is None:
        return {
            "account_id": account_id, "state": "stale", "value_minor": None, "as_of": None,
            "complete": False, "holdings": [], "addresses": [], "booked_balance": booked_balance, "reason": reason,
        }
    return {
        "account_id": account_id, "state": "stale", "value_minor": snapshot["value_minor"],
        "as_of": snapshot["as_of"], "complete": bool(snapshot["complete"]),
        "holdings": json.loads(snapshot["holdings_json"]), "addresses": json.loads(snapshot["addresses_json"]),
        "booked_balance": booked_balance, "reason": reason,
    }


def get_crypto_holdings(account_id: int, principal: AuthPrincipal) -> dict:
    """GET /accounts/{id}/crypto-holdings - Bestand je Coin + EUR-Wert über
    Port v2 (wallet_holdings), für alle Adressen die an dieses Konto gebunden
    sind.

    state wie get_crypto_value: unlinked|hidden|live|stale. "hidden": Konto
    ist von einem ANDEREN Mitglied verknüpft - der Port wird NICHT mit dem
    eigenen Usernamen für ein fremdes Konto aufgerufen.
    """
    with db() as conn:
        member = membership(conn, principal)
        household_id = member["household_id"]
        account = _require_wallet_owned_by(conn, household_id, account_id)
        booked_balance = _booked_balance(conn, account_id)
        links = _own_address_ids(conn, account_id)
        if not links:
            return {
                "account_id": account_id, "state": "unlinked", "value_minor": None, "as_of": None,
                "complete": False, "holdings": [], "addresses": [], "booked_balance": booked_balance, "reason": None,
            }
        linked_user_id = links[0]["linked_user_id"]
        if linked_user_id != principal.user_id:
            return {
                "account_id": account_id, "state": "hidden", "value_minor": None, "as_of": None,
                "complete": False, "holdings": [], "addresses": [], "booked_balance": booked_balance, "reason": None,
            }
        snapshot = _load_holdings_snapshot(conn, account_id)
        address_ids = [row["address_id"] for row in links]

    try:
        port = _load_port()
    except CryptoBridgeUnavailable as exc:
        return _stale_holdings_result(account_id, snapshot, booked_balance, exc.reason)
    if not hasattr(port, "wallet_holdings"):
        return _stale_holdings_result(account_id, snapshot, booked_balance, "port_incompatible")

    import asyncio

    try:
        result = asyncio.run(port.wallet_holdings(principal.username, address_ids))
    except port.WalletAddressNotFound as exc:
        raise coded(status.HTTP_404_NOT_FOUND, "crypto_address_not_found") from exc
    except port.PortfolioUnavailable:
        return _stale_holdings_result(account_id, snapshot, booked_balance, "portfolio_unavailable")

    with db(immediate=True) as conn:
        _store_holdings_snapshot(conn, account_id, household_id, result)
    return {
        "account_id": account_id, "state": "live", "value_minor": result["value_minor"],
        "as_of": result["as_of"], "complete": result["complete"], "holdings": result["holdings"],
        "addresses": result["addresses"], "booked_balance": booked_balance, "reason": None,
    }
