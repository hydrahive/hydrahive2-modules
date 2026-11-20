"""Crypto-Brücke (Phase 3): Verknüpfung mit Cryptoboard, Live-Wert, Trade-Import.

NUR lesend über `cryptoboard/backend/read_port.py` (PORT_VERSION 2, siehe
VERTRAG-PORT-V2.md). Keine Cryptoboard-Interna, kein Kurs-Client,
cryptoboard-Code bleibt unverändert. Diese Datei nutzt weiterhin nur die
v1-Funktionen (portfolios_for, portfolio_value, trades); die v2-Funktionen
(wallet_addresses_for, wallet_holdings) nutzt `crypto_addresses.py`.

Port-Zugang: `_load_port()` lädt das Modul über die Core-Registry
(`hydrahive.modules.registry.REGISTRY`) und validiert `PORT_VERSION`. Fehlt
das Modul, ist es nicht geladen, oder passt die Portversion nicht (z.B. noch
PORT_VERSION 1), wirft `_load_port()` `CryptoBridgeUnavailable` - fail-closed,
kein ungesicherter Fallback. In Tests wird `_load_port` per monkeypatch durch
einen Fake-Port ersetzt.

Der Port wird IMMER nur mit `principal.username` des anfragenden Users
aufgerufen, und nur wenn `principal.user_id == accounts.linked_user_id` -
nie mit dem Username eines anderen Haushaltsmitglieds.
"""

from __future__ import annotations

import hashlib
import importlib
import sqlite3
import time
from datetime import date

from fastapi import status
from hydrahive.api.middleware.auth import AuthPrincipal
from hydrahive.api.middleware.errors import coded
from hydrahive.db.connection import db

from . import audit
from .access import conflict, membership, require_row
from .common import NOW
from .import_inbox import insert_import_rows
from .import_parsers import NormalizedRecord
from .import_persistence import _batch_dict

PORT_VERSION = 2
_CRYPTO_CURRENCY = "EUR"
_TRADE_LIMIT = 1000


class CryptoBridgeUnavailable(RuntimeError):
    """Der Cryptoboard-Port ist nicht benutzbar - fail-closed, kein Fallback.

    `reason` ∈ {"module_missing", "module_not_loaded", "port_incompatible"}.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _load_port():
    """Lädt den Cryptoboard-Read-Port oder wirft CryptoBridgeUnavailable.

    In Tests per `monkeypatch.setattr(crypto_bridge, "_load_port", ...)`
    durch einen Fake-Port ersetzbar - kein echtes cryptoboard-Modul nötig.
    """
    from hydrahive.modules.registry import REGISTRY

    entry = REGISTRY.get("cryptoboard")
    if entry is None:
        raise CryptoBridgeUnavailable("module_missing")
    if not entry.loaded:
        raise CryptoBridgeUnavailable("module_not_loaded")
    try:
        port = importlib.import_module("hhmod_cryptoboard.read_port")
    except ImportError as exc:
        raise CryptoBridgeUnavailable("module_not_loaded") from exc
    if getattr(port, "PORT_VERSION", None) != PORT_VERSION:
        raise CryptoBridgeUnavailable("port_incompatible")
    return port


def _require_wallet_owned_by(conn: sqlite3.Connection, household_id: int, account_id: int) -> sqlite3.Row:
    return require_row(
        conn.execute(
            "SELECT * FROM module_haushaltsbuch_accounts WHERE id=? AND household_id=?",
            (account_id, household_id),
        ).fetchone(),
        "account_not_found",
    )


def _booked_balance(conn: sqlite3.Connection, account_id: int) -> int:
    """Gebuchter Saldo (Summe der Postings) eines Kontos - geteilt zwischen
    get_crypto_value (v1) und crypto_addresses.get_crypto_holdings (v2)."""
    return int(
        conn.execute(
            "SELECT COALESCE(SUM(base_amount),0) FROM module_haushaltsbuch_postings WHERE account_id=?",
            (account_id,),
        ).fetchone()[0]
    )


def get_status(principal: AuthPrincipal) -> dict:
    """GET /crypto-bridge/status - nur die eigenen Portfolios des Anfragenden."""
    with db() as conn:
        membership(conn, principal)
    try:
        port = _load_port()
    except CryptoBridgeUnavailable as exc:
        return {"available": False, "reason": exc.reason, "portfolios": []}
    portfolios = port.portfolios_for(principal.username)
    return {"available": True, "reason": None, "portfolios": portfolios}


def link_account(account_id: int, body, principal: AuthPrincipal) -> dict:
    """PUT /accounts/{id}/crypto-link - verknüpft ein Wallet-Konto mit einem
    Cryptoboard-Portfolio des anfragenden Users."""
    with db(immediate=True) as conn:
        member = membership(conn, principal)
        household_id = member["household_id"]
        account = _require_wallet_owned_by(conn, household_id, account_id)
        if account["revision"] != body.revision:
            conflict()
        if account["type"] != "wallet" or account["archived"]:
            raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "crypto_wallet_required")
        if account["linked_portfolio_id"] is not None:
            raise coded(status.HTTP_409_CONFLICT, "crypto_account_linked")
        household = conn.execute(
            "SELECT base_currency FROM module_haushaltsbuch_households WHERE id=?",
            (household_id,),
        ).fetchone()
        if household["base_currency"] != _CRYPTO_CURRENCY or account["currency"] != _CRYPTO_CURRENCY:
            raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "crypto_currency_unsupported")
        try:
            port = _load_port()
        except CryptoBridgeUnavailable as exc:
            raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "crypto_bridge_unavailable", reason=exc.reason) from exc
        portfolios = {item["id"] for item in port.portfolios_for(principal.username)}
        if body.portfolio_id not in portfolios:
            raise coded(status.HTTP_404_NOT_FOUND, "crypto_portfolio_not_found")
        try:
            cursor = conn.execute(
                f"UPDATE module_haushaltsbuch_accounts SET linked_portfolio_id=?,linked_user_id=?,"
                f"linked_at={NOW},revision=revision+1,updated_at={NOW} WHERE id=? AND household_id=? AND revision=?",
                (body.portfolio_id, principal.user_id, account_id, household_id, body.revision),
            )
        except sqlite3.IntegrityError as exc:
            raise coded(status.HTTP_409_CONFLICT, "crypto_portfolio_already_linked") from exc
        if not cursor.rowcount:
            conflict()
        audit.record(
            conn, household_id, principal.user_id, "account", account_id, "crypto_link",
            before={"linked_portfolio_id": None},
            after={"linked_portfolio_id": body.portfolio_id},
        )
        from .assets import account_with_balance

        result = account_with_balance(conn, account_id, principal)
    return result


def unlink_account(account_id: int, revision: int, principal: AuthPrincipal) -> dict:
    """DELETE /accounts/{id}/crypto-link - durch den Verknüpfer oder den
    Haushalts-Owner. Löscht den gespeicherten Snapshot (gibt keine Daten
    preis - der Saldo bleibt unverändert)."""
    with db(immediate=True) as conn:
        member = membership(conn, principal)
        household_id = member["household_id"]
        account = _require_wallet_owned_by(conn, household_id, account_id)
        if account["linked_portfolio_id"] is None:
            raise coded(status.HTTP_409_CONFLICT, "crypto_account_not_linked")
        if account["linked_user_id"] != principal.user_id and member["role"] != "owner":
            raise coded(status.HTTP_403_FORBIDDEN, "owner_only")
        cursor = conn.execute(
            f"UPDATE module_haushaltsbuch_accounts SET linked_portfolio_id=NULL,linked_user_id=NULL,"
            f"linked_at=NULL,revision=revision+1,updated_at={NOW} WHERE id=? AND household_id=? AND revision=?",
            (account_id, household_id, revision),
        )
        if not cursor.rowcount:
            conflict()
        conn.execute(
            "DELETE FROM module_haushaltsbuch_crypto_snapshots WHERE account_id=?", (account_id,)
        )
        audit.record(
            conn, household_id, principal.user_id, "account", account_id, "crypto_unlink",
            before={"linked_portfolio_id": account["linked_portfolio_id"]},
            after={"linked_portfolio_id": None},
        )
        from .assets import account_with_balance

        result = account_with_balance(conn, account_id, principal)
    return result


def _store_snapshot(conn: sqlite3.Connection, account_id: int, household_id: int, value_minor: int, complete: bool, as_of: str) -> None:
    conn.execute(
        "INSERT INTO module_haushaltsbuch_crypto_snapshots(account_id,household_id,value_minor,complete,as_of) "
        "VALUES(?,?,?,?,?) "
        "ON CONFLICT(account_id) DO UPDATE SET value_minor=excluded.value_minor,"
        "complete=excluded.complete,as_of=excluded.as_of",
        (account_id, household_id, value_minor, int(complete), as_of),
    )


def _load_snapshot(conn: sqlite3.Connection, account_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM module_haushaltsbuch_crypto_snapshots WHERE account_id=?", (account_id,)
    ).fetchone()


def get_crypto_value(account_id: int, principal: AuthPrincipal) -> dict:
    """GET /accounts/{id}/crypto-value.

    state:
    - "unlinked": Konto ist nicht verknüpft.
    - "hidden": Konto ist von einem ANDEREN Mitglied verknüpft - value_minor/
      as_of bleiben null, der Port wird NICHT aufgerufen (keine fremde
      Portfoliosicht).
    - "live": Port erfolgreich abgefragt (eigenes Portfolio); Snapshot wird
      aktualisiert.
    - "stale": Port nicht verfügbar oder PortfolioUnavailable -> letzter
      Snapshot (value_minor null, wenn keiner existiert), reason gesetzt.
    """
    with db() as conn:
        member = membership(conn, principal)
        household_id = member["household_id"]
        account = _require_wallet_owned_by(conn, household_id, account_id)
        booked_balance = _booked_balance(conn, account_id)
        if account["linked_portfolio_id"] is None:
            return {
                "account_id": account_id, "state": "unlinked", "value_minor": None,
                "as_of": None, "complete": False, "booked_balance": int(booked_balance), "reason": None,
            }
        if account["linked_user_id"] != principal.user_id:
            return {
                "account_id": account_id, "state": "hidden", "value_minor": None,
                "as_of": None, "complete": False, "booked_balance": int(booked_balance), "reason": None,
            }
        snapshot = _load_snapshot(conn, account_id)
        portfolio_id = account["linked_portfolio_id"]

    try:
        port = _load_port()
    except CryptoBridgeUnavailable as exc:
        return _stale_result(account_id, snapshot, int(booked_balance), exc.reason)

    import asyncio

    try:
        result = asyncio.run(port.portfolio_value(principal.username, portfolio_id))
    except port.PortfolioNotFound as exc:
        raise coded(status.HTTP_404_NOT_FOUND, "crypto_portfolio_not_found") from exc
    except port.PortfolioUnavailable:
        return _stale_result(account_id, snapshot, int(booked_balance), "portfolio_unavailable") 

    with db(immediate=True) as conn:
        member = membership(conn, principal)
        _store_snapshot(
            conn, account_id, member["household_id"], result["value_minor"], result["complete"], result["as_of"]
        )
    return {
        "account_id": account_id, "state": "live", "value_minor": result["value_minor"],
        "as_of": result["as_of"], "complete": result["complete"],
        "booked_balance": int(booked_balance), "reason": None,
    }


def _stale_result(account_id: int, snapshot: sqlite3.Row | None, booked_balance: int, reason: str) -> dict:
    if snapshot is None:
        return {
            "account_id": account_id, "state": "stale", "value_minor": None,
            "as_of": None, "complete": False, "booked_balance": booked_balance, "reason": reason,
        }
    return {
        "account_id": account_id, "state": "stale", "value_minor": snapshot["value_minor"],
        "as_of": snapshot["as_of"], "complete": bool(snapshot["complete"]),
        "booked_balance": booked_balance, "reason": reason,
    }


def _random_file_hash() -> str:
    """Eindeutiger file_hash für Crypto-Trade-Vorschau-Batches.

    Anders als beim echten Datei-Upload gibt es keine Datei, deren Inhalt
    dedupen könnte und soll: ein zweiter Trade-Import-Aufruf mit denselben
    Trades muss einen neuen Batch anlegen können, damit die Zeilen-
    Fingerprint-Logik (bank_reference -> strong) die Dedup-Arbeit übernimmt
    (siehe Vertrag: "zweiter Import -> Duplikate" ist Zeilen-, nicht
    Batch-Ebene). Deshalb hier zeitbasiert + Zufall statt aus den Trade-
    Daten abgeleitet.
    """
    import secrets

    return hashlib.sha256(f"{time.monotonic_ns()}:{secrets.token_hex(16)}".encode()).hexdigest()


def _trade_records(
    trades: list[dict], wallet_account_id: int, fee_category_id: int | None
) -> tuple[list[NormalizedRecord], int]:
    """Baut NormalizedRecord-Zeilen aus den Cryptoboard-Trades.

    Gibt die Zeilen plus die Anzahl übersprungener transfer_in/transfer_out-
    Trades zurück (für die Batch-Warnungen).
    """
    records: list[NormalizedRecord] = []
    skipped_transfers = 0
    for trade in trades:
        kind = trade["kind"]
        if kind not in ("buy", "sell"):
            skipped_transfers += 1
            continue
        executed_at = trade["executed_at"]
        booking_date = date.fromisoformat(str(executed_at)[:10])
        label = "Kauf" if kind == "buy" else "Verkauf"
        purpose = f"{label} {trade['quantity']} {trade['symbol']}"
        gross_minor = trade["gross_minor"]
        amount = -gross_minor if kind == "buy" else gross_minor
        source_line = len(records) + 1
        records.append(
            NormalizedRecord(
                source_line=source_line,
                booking_date=booking_date,
                value_date=booking_date,
                amount_minor=amount,
                currency=_CRYPTO_CURRENCY,
                counterparty="Cryptoboard",
                purpose=purpose,
                bank_reference=trade["ref"],
                counter_account_id=wallet_account_id,
            )
        )
        fee_minor = trade.get("fee_minor") or 0
        if fee_minor:
            records.append(
                NormalizedRecord(
                    source_line=len(records) + 1,
                    booking_date=booking_date,
                    value_date=booking_date,
                    amount_minor=-fee_minor,
                    currency=_CRYPTO_CURRENCY,
                    counterparty="Cryptoboard",
                    purpose=f"Cryptoboard-Gebühr {purpose}",
                    bank_reference=f"{trade['ref']}:fee",
                    category_id=fee_category_id,
                )
            )
    return records, skipped_transfers


def preview_trade_import(body, principal: AuthPrincipal) -> dict:
    """POST /crypto-bridge/trade-imports - legt einen Draft-Batch im
    bestehenden Prüfbereich an (wie POST /imports), ohne irgendetwas zu
    buchen. Nur der Verknüpfer des Wallets darf importieren."""
    with db(immediate=True) as conn:
        member = membership(conn, principal)
        household_id = member["household_id"]
        wallet = _require_wallet_owned_by(conn, household_id, body.wallet_account_id)
        if wallet["type"] != "wallet" or wallet["linked_portfolio_id"] is None:
            raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "crypto_wallet_not_linked")
        if wallet["linked_user_id"] != principal.user_id:
            raise coded(status.HTTP_403_FORBIDDEN, "crypto_link_owner_only")
        fiat_account = _require_wallet_owned_by(conn, household_id, body.fiat_account_id)
        if fiat_account["internal"] or fiat_account["type"] == "wallet" or fiat_account["archived"]:
            raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "crypto_fiat_account_invalid")
        household = conn.execute(
            "SELECT base_currency FROM module_haushaltsbuch_households WHERE id=?",
            (household_id,),
        ).fetchone()
        if (
            household["base_currency"] != _CRYPTO_CURRENCY
            or fiat_account["currency"] != _CRYPTO_CURRENCY
        ):
            raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "crypto_currency_unsupported")
        fee_category_id = body.fee_category_id
        if fee_category_id is not None:
            category = require_row(
                conn.execute(
                    "SELECT * FROM module_haushaltsbuch_categories WHERE id=? AND household_id=?",
                    (fee_category_id, household_id),
                ).fetchone(),
                "category_not_found",
            )
            if category["kind"] != "expense":
                raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "crypto_fee_category_invalid")

        try:
            port = _load_port()
        except CryptoBridgeUnavailable as exc:
            raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "crypto_bridge_unavailable", reason=exc.reason) from exc

        since = body.since.isoformat() if body.since else None
        try:
            trades = port.trades(
                principal.username, wallet["linked_portfolio_id"], since=since, limit=_TRADE_LIMIT
            )
        except port.PortfolioNotFound as exc:
            raise coded(status.HTTP_404_NOT_FOUND, "crypto_portfolio_not_found") from exc
        except port.PortfolioUnavailable as exc:
            raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "crypto_bridge_unavailable", reason="portfolio_unavailable") from exc

        records, skipped_transfers = _trade_records(trades, body.wallet_account_id, fee_category_id)
        if not records:
            raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "no_records")

        file_hash = _random_file_hash()
        cursor = conn.execute(
            "INSERT INTO module_haushaltsbuch_import_batches"
            "(household_id,account_id,display_filename,source_format,file_hash,created_by) VALUES(?,?,?,?,?,?)",
            (household_id, body.fiat_account_id, "Cryptoboard-Trades", "crypto_trades", file_hash, principal.user_id),
        )
        batch_id = int(cursor.lastrowid)
        insert_import_rows(conn, household_id, batch_id, body.fiat_account_id, fiat_account["currency"], records)
        batch = conn.execute(
            "SELECT * FROM module_haushaltsbuch_import_batches WHERE id=?", (batch_id,)
        ).fetchone()
        audit.record(
            conn, household_id, principal.user_id, "import_batch", batch_id, "create",
            after={
                "filename": "Cryptoboard-Trades", "format": "crypto_trades",
                "record_count": len(records), "skipped_transfers": skipped_transfers,
            },
        )
        result = _batch_dict(conn, batch, True)
    result["warnings"] = {"skipped_transfers": skipped_transfers}
    return result
