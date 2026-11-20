"""Crypto-Trade-Import (Phase 3, v1): Vorschau-Batch aus Cryptoboard-Trades
im bestehenden Prüfbereich (POST /crypto-bridge/trade-imports), ausgelagert
aus crypto_bridge.py (Dateigrößenlimit). Nutzt dieselbe Port-Grundlage
(PORT_VERSION, _load_port, CryptoBridgeUnavailable, _require_wallet_owned_by)
aus crypto_bridge.py über die Modulreferenz - NICHT per `from .crypto_bridge
import _load_port` (siehe Hinweis dort zum monkeypatch).
"""

from __future__ import annotations

import hashlib
import time
from datetime import date

from fastapi import status
from hydrahive.api.middleware.auth import AuthPrincipal
from hydrahive.api.middleware.errors import coded
from hydrahive.db.connection import db

from . import audit, crypto_bridge
from .access import membership, require_row
from .crypto_bridge import CryptoBridgeUnavailable, _CRYPTO_CURRENCY, _TRADE_LIMIT, _require_wallet_owned_by
from .import_inbox import insert_import_rows
from .import_parsers import NormalizedRecord
from .import_persistence import _batch_dict


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
            port = crypto_bridge._load_port()
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
