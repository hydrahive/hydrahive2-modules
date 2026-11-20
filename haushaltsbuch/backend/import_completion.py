from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import status
from hydrahive.api.middleware.auth import AuthPrincipal
from hydrahive.api.middleware.errors import coded
from hydrahive.db.connection import db

from . import audit, ledger
from .access import conflict, membership, require_row
from .common import NOW
from .import_persistence import _batch_dict
from .models import PostingIn, TransactionCreate

_NO_CATEGORY_NAME = "Ohne Kategorie"


def _ensure_no_category(conn, household_id: int) -> int:
    """System-Ausgabenkategorie "Ohne Kategorie" (VERTRAG-B.md): wird je
    Haushalt einmal angelegt (internal=1, bleibt in list_categories
    SICHTBAR/wählbar - Till soll sie sehen, filtern (C3) und später
    umkategorisieren können). Kartenzahlungen/Abgänge aus crypto_ledger
    sollen OHNE echte Kategorie buchbar sein (Till weist sie selbst zu,
    Zieldokument Punkt 4) - kein Raten einer echten Kategorie."""
    row = conn.execute(
        "SELECT id FROM module_haushaltsbuch_categories WHERE household_id=? AND internal=1 AND name=?",
        (household_id, _NO_CATEGORY_NAME),
    ).fetchone()
    if row is not None:
        return row["id"]
    cursor = conn.execute(
        "INSERT INTO module_haushaltsbuch_categories(household_id,name,kind,internal) VALUES(?,?,'expense',1)",
        (household_id, _NO_CATEGORY_NAME),
    )
    return int(cursor.lastrowid)


def _require_own_crypto_account(conn, household_id: int, account_id: int, user_id: str) -> None:
    """Wallet<->Wallet-Prüfung für crypto_ledger-Transferzeilen: beide Konten
    müssen über module_haushaltsbuch_account_crypto_addresses an EIGENE
    Adressen des Abschließenden gebunden sein - anders als bei crypto_trades
    (dort prüft linked_portfolio_id auf dem einzigen Wallet-Konto)."""
    row = conn.execute(
        "SELECT linked_user_id FROM module_haushaltsbuch_account_crypto_addresses "
        "WHERE household_id=? AND account_id=? LIMIT 1",
        (household_id, account_id),
    ).fetchone()
    if row is None:
        raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "crypto_wallet_not_linked")
    if row["linked_user_id"] != user_id:
        raise coded(status.HTTP_403_FORBIDDEN, "crypto_link_owner_only")


def complete_batch(batch_id: int, revision: int, principal: AuthPrincipal) -> dict:
    with db(immediate=True) as conn:
        member = membership(conn, principal)
        household_id = member["household_id"]
        batch = require_row(conn.execute(
            "SELECT * FROM module_haushaltsbuch_import_batches WHERE id=? AND household_id=?",
            (batch_id, household_id),
        ).fetchone(), "import_batch_not_found")
        if batch["status"] != "draft" or batch["revision"] != revision:
            conflict("import_batch_already_changed")
        rows = conn.execute(
            "SELECT * FROM module_haushaltsbuch_import_rows WHERE batch_id=? AND status='accepted' ORDER BY id",
            (batch_id,),
        ).fetchall()
        if not rows:
            raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "no_accepted_import_rows")
        for row in rows:
            if (
                row["booking_date"] is None
                or row["amount_minor"] is None
                or row["currency"] is None
            ):
                raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "import_row_incomplete")
            amount = row["amount_minor"]
            account_id = row["row_account_id"] or batch["account_id"]
            account = require_row(conn.execute(
                "SELECT * FROM module_haushaltsbuch_accounts WHERE id=? AND household_id=?",
                (account_id, household_id),
            ).fetchone(), "account_not_found")
            if row["counter_account_id"] is not None:
                # Transfer-Zeile (Crypto-Trade- oder Crypto-Ledger-Import,
                # Konto<->Konto-Umbuchung): keine Kategorie nötig, stattdessen
                # ein zweites Konto-Posting auf dem Gegenkonto.
                counter_account = require_row(conn.execute(
                    "SELECT * FROM module_haushaltsbuch_accounts WHERE id=? AND household_id=?",
                    (row["counter_account_id"], household_id),
                ).fetchone(), "account_not_found")
                if batch["source_format"] == "crypto_trades":
                    # Gleiche Bedingung wie beim Anlegen (crypto_bridge.preview_trade_import):
                    # Wallet noch verknüpft, und zwar vom Abschließenden. Sonst würde ein vor dem
                    # Trennen angelegter Entwurf auf ein unverknüpftes Wallet buchen (Review 19.11.).
                    if counter_account["linked_portfolio_id"] is None:
                        raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "crypto_wallet_not_linked")
                    if counter_account["linked_user_id"] != principal.user_id:
                        raise coded(status.HTTP_403_FORBIDDEN, "crypto_link_owner_only")
                elif batch["source_format"] == "crypto_ledger":
                    # Swap = Umbuchung zwischen Tills EIGENEN Krypto-Konten
                    # (VERTRAG-B.md) - Prüfung über crypto_addresses, nicht
                    # linked_portfolio_id (das Konto trägt hier keine Portfolio-
                    # Verknüpfung, sondern Adressen je Chain).
                    _require_own_crypto_account(conn, household_id, account["id"], principal.user_id)
                    _require_own_crypto_account(conn, household_id, counter_account["id"], principal.user_id)
                postings = [
                    PostingIn(account_id=account["id"], original_amount=amount, currency=row["currency"], base_amount=amount),
                    PostingIn(account_id=counter_account["id"], original_amount=-amount, currency=row["currency"], base_amount=-amount),
                ]
            else:
                category_id = row["category_id"]
                if category_id is None:
                    if batch["source_format"] != "crypto_ledger":
                        raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "import_category_required")
                    # Kartenzahlung/Abgang ohne Kategorie (Till weist sie
                    # später selbst zu, Zieldokument Punkt 4) -> System-
                    # Ausgabenkategorie statt Kategoriezwang.
                    category_id = _ensure_no_category(conn, household_id)
                category = require_row(conn.execute(
                    "SELECT * FROM module_haushaltsbuch_categories WHERE id=? AND household_id=?",
                    (category_id, household_id),
                ).fetchone(), "category_not_found")
                expected_kind = "income" if row["amount_minor"] > 0 else "expense"
                if category["kind"] != expected_kind:
                    raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "import_category_kind_mismatch")
                postings = [
                    PostingIn(account_id=account["id"], original_amount=amount, currency=row["currency"], base_amount=amount),
                    PostingIn(category_id=category["id"], original_amount=-amount, currency=row["currency"], base_amount=-amount),
                ]
            body = TransactionCreate(
                booking_date=row["booking_date"], value_date=row["value_date"],
                counterparty=row["counterparty"], purpose=row["purpose"],
                note=f"Import #{batch_id}, Zeile {row['source_line']}", source="import",
                postings=postings,
            )
            transaction = ledger._insert(conn, household_id, body, principal.user_id)
            conn.execute(
                f"UPDATE module_haushaltsbuch_import_rows SET status='imported',transaction_id=?,revision=revision+1,updated_at={NOW} WHERE id=?",
                (transaction["id"], row["id"]),
            )
            audit.record(conn, household_id, principal.user_id, "transaction", transaction["id"], "create_import", after={"import_batch_id": batch_id, "import_row_id": row["id"]})
        conn.execute(
            f"UPDATE module_haushaltsbuch_import_batches SET status='imported',revision=revision+1,completed_at={NOW},updated_at={NOW} WHERE id=?",
            (batch_id,),
        )
        audit.record(conn, household_id, principal.user_id, "import_batch", batch_id, "complete", after={"transaction_count": len(rows)})
        result = _batch_dict(conn, conn.execute("SELECT * FROM module_haushaltsbuch_import_batches WHERE id=?", (batch_id,)).fetchone(), True)
    return result


def reverse_batch(batch_id: int, revision: int, principal: AuthPrincipal) -> dict:
    with db(immediate=True) as conn:
        member = membership(conn, principal)
        batch = require_row(conn.execute(
            "SELECT * FROM module_haushaltsbuch_import_batches WHERE id=? AND household_id=?",
            (batch_id, member["household_id"]),
        ).fetchone(), "import_batch_not_found")
        if batch["status"] != "imported" or batch["revision"] != revision:
            conflict("import_batch_already_changed")
        rows = conn.execute(
            "SELECT * FROM module_haushaltsbuch_import_rows WHERE batch_id=? AND status='imported' ORDER BY id",
            (batch_id,),
        ).fetchall()
        timezone_name = conn.execute(
            "SELECT timezone FROM module_haushaltsbuch_households WHERE id=?", (member["household_id"],)
        ).fetchone()[0]
        reversal_date = datetime.now(ZoneInfo(timezone_name)).date()
        for row in rows:
            transaction = require_row(conn.execute(
                "SELECT * FROM module_haushaltsbuch_transactions WHERE id=? AND household_id=?",
                (row["transaction_id"], member["household_id"]),
            ).fetchone(), "transaction_not_found")
            if transaction["status"] == "reversed":
                conn.execute(
                    f"UPDATE module_haushaltsbuch_import_rows SET status='reversed',"
                    f"revision=revision+1,updated_at={NOW} WHERE id=?",
                    (row["id"],),
                )
                continue
            posting_rows = conn.execute(
                "SELECT * FROM module_haushaltsbuch_postings WHERE transaction_id=? ORDER BY id", (transaction["id"],)
            ).fetchall()
            body = TransactionCreate(
                booking_date=reversal_date, value_date=reversal_date,
                counterparty=transaction["counterparty"], purpose=f"Storno: {transaction['purpose'] or transaction['id']}",
                source="import",
                postings=[PostingIn(
                    account_id=item["account_id"], category_id=item["category_id"],
                    original_amount=-item["original_amount"], currency=item["currency"], base_amount=-item["base_amount"],
                    exchange_rate=item["exchange_rate"], exchange_rate_date=item["exchange_rate_date"],
                    exchange_rate_source=item["exchange_rate_source"], member_id=item["member_id"],
                ) for item in posting_rows],
            )
            reversal = ledger._insert(conn, member["household_id"], body, principal.user_id, reversal_of=transaction["id"], allow_archived=True)
            conn.execute(f"UPDATE module_haushaltsbuch_transactions SET status='reversed',revision=revision+1,updated_at={NOW} WHERE id=?", (transaction["id"],))
            conn.execute(f"UPDATE module_haushaltsbuch_import_rows SET status='reversed',revision=revision+1,updated_at={NOW} WHERE id=?", (row["id"],))
            audit.record(conn, member["household_id"], principal.user_id, "transaction", transaction["id"], "reverse_import", after={"reversal_id": reversal["id"], "import_batch_id": batch_id})
        conn.execute(f"UPDATE module_haushaltsbuch_import_batches SET status='reversed',revision=revision+1,reversed_at={NOW},updated_at={NOW} WHERE id=?", (batch_id,))
        audit.record(conn, member["household_id"], principal.user_id, "import_batch", batch_id, "reverse", after={"transaction_count": len(rows)})
        result = _batch_dict(conn, conn.execute("SELECT * FROM module_haushaltsbuch_import_batches WHERE id=?", (batch_id,)).fetchone(), True)
    return result
