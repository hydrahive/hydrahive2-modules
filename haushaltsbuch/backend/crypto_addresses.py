"""Crypto-Brücke v2 (Etappe A1/A2, VERTRAG-PORT-V2.md): Konto <-> Cryptoboard-
ADRESSEN (statt nur Portfolio wie in crypto_bridge.py/v1) + Bestand je Coin
mit EUR-Wert.

NUR lesend über `cryptoboard/backend/read_port.py` (PORT_VERSION 2:
wallet_addresses_for, wallet_holdings). Fail-closed wie die v1-Brücke: ist
der Port nicht verfügbar oder noch v1, liefert get_crypto_holdings den
letzten Holdings-Snapshot (state "stale") statt eines Fehlers.

Der Port wird IMMER nur mit `principal.username` aufgerufen, und nur wenn
`principal.user_id == accounts.linked_user_id` (geprüft über die
Verknüpfungszeilen dieses Kontos) - nie mit dem Username eines anderen
Haushaltsmitglieds (gleiche Regel wie crypto_bridge.py).
"""

from __future__ import annotations

import json
import sqlite3

from fastapi import status
from hydrahive.api.middleware.auth import AuthPrincipal
from hydrahive.api.middleware.errors import coded
from hydrahive.db.connection import db

from . import audit
from .access import conflict, membership
from . import crypto_bridge
from .crypto_bridge import CryptoBridgeUnavailable, _require_wallet_owned_by


def get_addresses(principal: AuthPrincipal) -> list[dict]:
    """GET /crypto-bridge/addresses - eigene Cryptoboard-Adressen, je Eintrag
    `linked_account_id` (an welches Konto DIESES Haushalts sie ggf. schon
    gebunden ist, sonst None)."""
    with db() as conn:
        member = membership(conn, principal)
        household_id = member["household_id"]
        links = {
            row["address_id"]: row["account_id"]
            for row in conn.execute(
                "SELECT address_id,account_id FROM module_haushaltsbuch_account_crypto_addresses "
                "WHERE household_id=? AND linked_user_id=?",
                (household_id, principal.user_id),
            ).fetchall()
        }
    try:
        port = crypto_bridge._load_port()
    except CryptoBridgeUnavailable as exc:
        raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "crypto_bridge_unavailable", reason=exc.reason) from exc
    if not hasattr(port, "wallet_addresses_for"):
        raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "crypto_bridge_unavailable", reason="port_incompatible")
    addresses = port.wallet_addresses_for(principal.username)
    return [{**address, "linked_account_id": links.get(address["id"])} for address in addresses]


def _own_address_ids(conn: sqlite3.Connection, account_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM module_haushaltsbuch_account_crypto_addresses WHERE account_id=? ORDER BY id",
        (account_id,),
    ).fetchall()


def link_addresses(account_id: int, body, principal: AuthPrincipal) -> dict:
    """PUT /accounts/{id}/crypto-addresses - ersetzt die Adressliste des
    Wallet-Kontos durch `body.address_ids` (nur eigene Adressen, nur ein
    Konto je Adresse)."""
    with db(immediate=True) as conn:
        member = membership(conn, principal)
        household_id = member["household_id"]
        account = _require_wallet_owned_by(conn, household_id, account_id)
        if account["revision"] != body.revision:
            conflict()
        if account["type"] != "wallet" or account["archived"]:
            raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "crypto_wallet_required")
        if not body.address_ids:
            raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "crypto_addresses_required")
        try:
            port = crypto_bridge._load_port()
        except CryptoBridgeUnavailable as exc:
            raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "crypto_bridge_unavailable", reason=exc.reason) from exc
        if not hasattr(port, "wallet_addresses_for"):
            raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "crypto_bridge_unavailable", reason="port_incompatible")
        own = {a["id"]: a for a in port.wallet_addresses_for(principal.username)}
        missing = [aid for aid in body.address_ids if aid not in own]
        if missing:
            raise coded(status.HTTP_404_NOT_FOUND, "crypto_address_not_found")

        before = [dict(row) for row in _own_address_ids(conn, account_id)]
        conn.execute("DELETE FROM module_haushaltsbuch_account_crypto_addresses WHERE account_id=?", (account_id,))
        try:
            for aid in body.address_ids:
                address = own[aid]
                conn.execute(
                    "INSERT INTO module_haushaltsbuch_account_crypto_addresses"
                    "(account_id,household_id,linked_user_id,address_id,chain,address) VALUES(?,?,?,?,?,?)",
                    (account_id, household_id, principal.user_id, aid, address["chain"], address["address"]),
                )
        except sqlite3.IntegrityError as exc:
            raise coded(status.HTTP_409_CONFLICT, "crypto_address_already_linked") from exc

        cursor = conn.execute(
            "UPDATE module_haushaltsbuch_accounts SET linked_user_id=?,revision=revision+1,"
            "updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=? AND household_id=? AND revision=?",
            (principal.user_id, account_id, household_id, body.revision),
        )
        if not cursor.rowcount:
            conflict()
        audit.record(
            conn, household_id, principal.user_id, "account", account_id, "crypto_addresses_link",
            before={"address_ids": [row["address_id"] for row in before]},
            after={"address_ids": list(body.address_ids)},
        )
        from .assets import account_with_balance

        result = account_with_balance(conn, account_id, principal)
    return result


def unlink_addresses(account_id: int, revision: int, principal: AuthPrincipal) -> dict:
    """DELETE /accounts/{id}/crypto-addresses?revision= - löst alle Adressen
    dieses Kontos und löscht den Holdings-Snapshot."""
    with db(immediate=True) as conn:
        member = membership(conn, principal)
        household_id = member["household_id"]
        account = _require_wallet_owned_by(conn, household_id, account_id)
        existing = _own_address_ids(conn, account_id)
        if not existing:
            raise coded(status.HTTP_409_CONFLICT, "crypto_account_not_linked")
        linked_user_id = existing[0]["linked_user_id"]
        if linked_user_id != principal.user_id and member["role"] != "owner":
            raise coded(status.HTTP_403_FORBIDDEN, "owner_only")
        cursor = conn.execute(
            "UPDATE module_haushaltsbuch_accounts SET revision=revision+1,"
            "updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=? AND household_id=? AND revision=?",
            (account_id, household_id, revision),
        )
        if not cursor.rowcount:
            conflict()
        conn.execute("DELETE FROM module_haushaltsbuch_account_crypto_addresses WHERE account_id=?", (account_id,))
        conn.execute(
            "DELETE FROM module_haushaltsbuch_crypto_holdings_snapshots WHERE account_id=?", (account_id,)
        )
        audit.record(
            conn, household_id, principal.user_id, "account", account_id, "crypto_addresses_unlink",
            before={"address_ids": [row["address_id"] for row in existing]},
            after={"address_ids": []},
        )
        from .assets import account_with_balance

        result = account_with_balance(conn, account_id, principal)
    return result
