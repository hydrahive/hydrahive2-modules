"""Zeilenaufbau für den Crypto-Ledger-Import (ausgelagert aus
crypto_ledger_import.py, Dateigrößenlimit): Klassifiziert einen einzelnen
`ledger_moves`-Eintrag (Read-Port v3) in Swap/Kartenzahlung/Abgang/unklar
und baut daraus den passenden `NormalizedRecord`.

Kontozuordnung über chain: GENAU EIN Konto mit verknüpfter Adresse dieser
Chain (module_haushaltsbuch_account_crypto_addresses, linked_user_id des
Aufrufenden) - mehrere oder keine Treffer -> unklar (nicht geraten).
"""

from __future__ import annotations

import sqlite3
from datetime import date

from .crypto_bridge import _CRYPTO_CURRENCY
from .import_parsers import NormalizedRecord


def account_for_chain(
    conn: sqlite3.Connection, household_id: int, user_id: str, chain: str | None
) -> int | None:
    """Genau EIN Konto mit verknüpfter Adresse dieser Chain - sonst None
    (kein Raten, die Zeile wird 'unklar')."""
    if not chain:
        return None
    rows = conn.execute(
        "SELECT DISTINCT account_id FROM module_haushaltsbuch_account_crypto_addresses "
        "WHERE household_id=? AND linked_user_id=? AND chain=?",
        (household_id, user_id, chain),
    ).fetchall()
    if len(rows) != 1:
        return None
    return rows[0]["account_id"]


def classify_move(conn: sqlite3.Connection, household_id: int, user_id: str, move: dict) -> dict:
    """Ordnet einen ledger_moves-Eintrag einer Gruppe zu. Gibt für buchbare
    Einträge {"group","record" (source_line noch 0),"account_id",
    "value_minor"} zurück, für unklare {"group":"unklar","id","reason"}."""
    move_type = move.get("type")
    move_id = move.get("id")

    if move_type == "unklar":
        return {"group": "unklar", "id": move_id, "reason": move.get("reason") or "unklar"}

    executed_at = move.get("executed_at")
    booking_date = date.fromisoformat(str(executed_at)[:10]) if executed_at else None

    if move_type == "swap":
        from_leg, to_leg = move.get("from") or {}, move.get("to") or {}
        value_minor = move.get("value_minor")
        from_account = account_for_chain(conn, household_id, user_id, from_leg.get("chain"))
        to_account = account_for_chain(conn, household_id, user_id, to_leg.get("chain"))
        if from_account is None or to_account is None:
            return {"group": "unklar", "id": move_id, "reason": "kein_eindeutiges_konto"}
        if value_minor is None:
            return {"group": "unklar", "id": move_id, "reason": "value_minor_fehlt"}
        record = NormalizedRecord(
            source_line=0, booking_date=booking_date, value_date=booking_date,
            amount_minor=-value_minor, currency=_CRYPTO_CURRENCY, counterparty="Cryptoboard",
            purpose=f"Swap {from_leg.get('symbol')} \u2192 {to_leg.get('symbol')}",
            bank_reference=move_id, counter_account_id=to_account, row_account_id=from_account,
        )
        return {"group": "swap", "record": record, "account_id": from_account, "value_minor": value_minor}

    if move_type in ("kartenzahlung", "abgang"):
        value_minor = move.get("value_minor")
        account_id = account_for_chain(conn, household_id, user_id, move.get("chain"))
        if account_id is None:
            return {"group": "unklar", "id": move_id, "reason": "kein_eindeutiges_konto"}
        if value_minor is None:
            return {"group": "unklar", "id": move_id, "reason": "value_minor_fehlt"}
        if value_minor == 0:
            # z. B. 0,002466 USDC (Karten-Prüfbuchung): unter 1 Cent, als Buchung nicht annehmbar
            # (invalid_amount) - sichtbar als unklar statt still verschluckt (Live-Probe 21.11.2026).
            return {"group": "unklar", "id": move_id, "reason": "betrag_unter_1_cent"}
        label = "Kartenzahlung" if move_type == "kartenzahlung" else "Abgang"
        record = NormalizedRecord(
            source_line=0, booking_date=booking_date, value_date=booking_date,
            amount_minor=-value_minor, currency=_CRYPTO_CURRENCY, counterparty="Cryptoboard",
            purpose=f"{label} {move.get('quantity')} {move.get('symbol')}",
            bank_reference=move_id, row_account_id=account_id,
        )
        return {"group": move_type, "record": record, "account_id": account_id, "value_minor": value_minor}

    return {"group": "unklar", "id": move_id, "reason": "unbekannter_typ"}


def unklar_record(source_line: int, item: dict) -> NormalizedRecord:
    return NormalizedRecord(
        source_line=source_line, booking_date=None, value_date=None, amount_minor=None,
        currency=None, counterparty="Cryptoboard", purpose="Nicht eindeutig zuordenbar",
        bank_reference=item.get("id"), errors=(f"crypto_ledger_{item['reason']}",),
    )
