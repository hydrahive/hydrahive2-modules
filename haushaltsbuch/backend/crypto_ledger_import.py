"""Crypto-Ledger-Import (Etappe B, VERTRAG-B.md): Vorschau-Batch aus dem
Cryptoboard-Ledger (Read-Port v3, `ledger_moves`) - ausgelagert aus
crypto_bridge.py (Dateigrößenlimit), nutzt dieselbe Port-Grundlage über die
Modulreferenz (`from . import crypto_bridge` + `crypto_bridge._load_port()`,
NICHT `from .crypto_bridge import _load_port` - sonst greift der monkeypatch
in den Tests nicht).

Drei Gruppen, household-weit (kein Portfolio/Wallet-Parameter nötig - jedes
verknüpfte Konto des Users wird über seine Chain gefunden):
- Swap: Transfer-Zeile Von-Konto -> Nach-Konto (counter_account_id), NIE
  Einnahme/Ausgabe.
- Kartenzahlung/Abgang: Ausgabe-Zeile vom jeweiligen Krypto-Konto
  (row_account_id), Kategorie optional (Till weist sie zu - import_completion
  bucht das Gegenposting ohne Kategorie auf "Ohne Kategorie").
  Abgang-Zeilen werden nach dem Einfügen auf status='rejected' gesetzt -
  standardmäßig ausgeschlossen (Till entscheidet, Zieldokument §6 Punkt 4).
- Unklar (fehlendes Swap-Bein, kein eindeutiges Konto, value_minor None,
  unbekannter Typ): Zeile mit Fehlercode, nicht buchbar.

Kontozuordnung über chain: GENAU EIN Konto mit verknüpfter Adresse dieser
Chain (module_haushaltsbuch_account_crypto_addresses, linked_user_id des
Aufrufenden) - mehrere oder keine Treffer -> unklar (nicht geraten).

Dedup: stabile Kennung = ledger_moves-Eintrag.id als bank_reference/
Fingerprint (import_inbox.insert_import_rows dedupt automatisch über den
bestehenden Fingerprint-Mechanismus); ein zweiter Aufruf liefert dieselben
Zeilen als 'duplicate' zurück, 0 neue buchbare.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import replace
from datetime import date

from fastapi import status
from hydrahive.api.middleware.auth import AuthPrincipal
from hydrahive.api.middleware.errors import coded
from hydrahive.db.connection import db

from . import audit, crypto_bridge
from .access import membership
from .crypto_bridge import CryptoBridgeUnavailable, _CRYPTO_CURRENCY
from .import_inbox import insert_import_rows
from .import_parsers import NormalizedRecord
from .import_persistence import _batch_dict

_LEDGER_LIMIT = 5000
_GROUP_LABEL = {"swap": "swaps", "kartenzahlung": "kartenzahlungen", "abgang": "abgaenge"}


def _random_file_hash() -> str:
    """Eindeutiger file_hash für die Ledger-Vorschau - wie bei
    crypto_trade_import._random_file_hash(): kein echter Datei-Inhalt zum
    Dedupen, die Zeilen-Fingerprint-Logik übernimmt die Dedup-Arbeit."""
    import secrets

    return hashlib.sha256(f"{time.monotonic_ns()}:{secrets.token_hex(16)}".encode()).hexdigest()


def _account_for_chain(conn, household_id: int, user_id: str, chain: str) -> int | None:
    """Genau EIN Konto mit verknüpfter Adresse dieser Chain - sonst None
    (kein Raten, die Zeile wird 'unklar')."""
    rows = conn.execute(
        "SELECT DISTINCT account_id FROM module_haushaltsbuch_account_crypto_addresses "
        "WHERE household_id=? AND linked_user_id=? AND chain=?",
        (household_id, user_id, chain),
    ).fetchall()
    if len(rows) != 1:
        return None
    return rows[0]["account_id"]


def _classify(conn, household_id: int, user_id: str, move: dict) -> dict:
    """Ordnet einen ledger_moves-Eintrag einer Gruppe zu. Gibt für buchbare
    Einträge {"group","record" (ohne source_line),"account_id","value_minor"}
    zurück, für unklare {"group":"unklar","id","reason"}."""
    move_type = move.get("type")
    move_id = move.get("id")

    if move_type == "unklar":
        return {"group": "unklar", "id": move_id, "reason": move.get("reason") or "unklar"}

    executed_at = move.get("executed_at")
    booking_date = date.fromisoformat(str(executed_at)[:10]) if executed_at else None

    if move_type == "swap":
        from_leg, to_leg = move.get("from") or {}, move.get("to") or {}
        value_minor = move.get("value_minor")
        from_account = _account_for_chain(conn, household_id, user_id, from_leg.get("chain"))
        to_account = _account_for_chain(conn, household_id, user_id, to_leg.get("chain"))
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
        account_id = _account_for_chain(conn, household_id, user_id, move.get("chain"))
        if account_id is None:
            return {"group": "unklar", "id": move_id, "reason": "kein_eindeutiges_konto"}
        if value_minor is None:
            return {"group": "unklar", "id": move_id, "reason": "value_minor_fehlt"}
        label = "Kartenzahlung" if move_type == "kartenzahlung" else "Abgang"
        record = NormalizedRecord(
            source_line=0, booking_date=booking_date, value_date=booking_date,
            amount_minor=-value_minor, currency=_CRYPTO_CURRENCY, counterparty="Cryptoboard",
            purpose=f"{label} {move.get('quantity')} {move.get('symbol')}",
            bank_reference=move_id, row_account_id=account_id,
        )
        return {"group": move_type, "record": record, "account_id": account_id, "value_minor": value_minor}

    return {"group": "unklar", "id": move_id, "reason": "unbekannter_typ"}


def _unklar_record(source_line: int, item: dict) -> NormalizedRecord:
    return NormalizedRecord(
        source_line=source_line, booking_date=None, value_date=None, amount_minor=None,
        currency=None, counterparty="Cryptoboard", purpose="Nicht eindeutig zuordenbar",
        bank_reference=item.get("id"), errors=(f"crypto_ledger_{item['reason']}",),
    )


def preview_ledger_import(principal: AuthPrincipal) -> dict:
    """POST /crypto-bridge/ledger-imports - household-weit, kein Portfolio-
    Parameter nötig. Legt einen Draft-Batch im bestehenden Prüfbereich an
    (wie POST /imports), ohne irgendetwas zu buchen."""
    with db(immediate=True) as conn:
        member = membership(conn, principal)
        household_id = member["household_id"]
        own_accounts = conn.execute(
            "SELECT DISTINCT account_id FROM module_haushaltsbuch_account_crypto_addresses "
            "WHERE household_id=? AND linked_user_id=?",
            (household_id, principal.user_id),
        ).fetchall()
        if not own_accounts:
            raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "crypto_wallet_not_linked")
        batch_account_id = min(row["account_id"] for row in own_accounts)

        try:
            port = crypto_bridge._load_port()
        except CryptoBridgeUnavailable as exc:
            raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "crypto_bridge_unavailable", reason=exc.reason) from exc
        if not hasattr(port, "ledger_moves"):
            raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "crypto_bridge_unavailable", reason="port_incompatible")
        try:
            moves = port.ledger_moves(principal.username, limit=_LEDGER_LIMIT)
        except port.PortfolioUnavailable as exc:
            raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "crypto_bridge_unavailable", reason="portfolio_unavailable") from exc

        classified = [_classify(conn, household_id, principal.user_id, move) for move in moves]
        groups_source: dict[str, list[dict]] = {"swap": [], "kartenzahlung": [], "abgang": []}
        unklar: list[dict] = []
        for item in classified:
            if item["group"] == "unklar":
                unklar.append({"id": item.get("id"), "reason": item["reason"]})
            else:
                groups_source[item["group"]].append(item)

        if not any(groups_source.values()):
            raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "no_records")

        file_hash = _random_file_hash()
        cursor = conn.execute(
            "INSERT INTO module_haushaltsbuch_import_batches"
            "(household_id,account_id,display_filename,source_format,file_hash,created_by) VALUES(?,?,?,?,?,?)",
            (household_id, batch_account_id, "Cryptoboard-Ledger", "crypto_ledger", file_hash, principal.user_id),
        )
        batch_id = int(cursor.lastrowid)

        source_line = 0
        abgang_refs: list[str] = []
        for group_name, items in groups_source.items():
            by_account: dict[int, list[NormalizedRecord]] = {}
            for item in items:
                source_line += 1
                by_account.setdefault(item["account_id"], []).append(
                    replace(item["record"], source_line=source_line)
                )
                if group_name == "abgang":
                    abgang_refs.append(item["record"].bank_reference)
            for account_id, records in by_account.items():
                insert_import_rows(conn, household_id, batch_id, account_id, _CRYPTO_CURRENCY, records)
        unklar_records = [_unklar_record(source_line + i + 1, item) for i, item in enumerate(unklar)]
        if unklar_records:
            insert_import_rows(conn, household_id, batch_id, batch_account_id, _CRYPTO_CURRENCY, unklar_records)

        rows = conn.execute(
            "SELECT bank_reference,status FROM module_haushaltsbuch_import_rows WHERE batch_id=?",
            (batch_id,),
        ).fetchall()
        status_by_ref = {row["bank_reference"]: row["status"] for row in rows}
        if abgang_refs:
            conn.execute(
                "UPDATE module_haushaltsbuch_import_rows SET status='rejected',revision=revision+1 "
                "WHERE batch_id=? AND status='pending' AND bank_reference IN ("
                + ",".join("?" * len(abgang_refs)) + ")",
                (batch_id, *abgang_refs),
            )

        duplicates = sum(1 for s in status_by_ref.values() if s == "duplicate")
        groups: dict = {"unklar": unklar, "duplicates": duplicates}
        for group_name, items in groups_source.items():
            fresh = [item for item in items if status_by_ref.get(item["record"].bank_reference) != "duplicate"]
            groups[_GROUP_LABEL[group_name]] = {
                "count": len(fresh),
                "sum_minor": sum(item["value_minor"] for item in fresh),
            }

        batch = conn.execute(
            "SELECT * FROM module_haushaltsbuch_import_batches WHERE id=?", (batch_id,)
        ).fetchone()
        audit.record(
            conn, household_id, principal.user_id, "import_batch", batch_id, "create",
            after={
                "filename": "Cryptoboard-Ledger", "format": "crypto_ledger",
                "record_count": len(rows), "groups": groups,
            },
        )
        result = _batch_dict(conn, batch, True)
    result["groups"] = groups
    return result
