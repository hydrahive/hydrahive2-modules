"""Crypto-Ledger-Import (Etappe B, VERTRAG-B.md): Vorschau-Batch aus dem
Cryptoboard-Ledger (Read-Port v3, `ledger_moves`) - ausgelagert aus
crypto_bridge.py (Dateigrößenlimit); der Zeilenaufbau selbst liegt in
crypto_ledger_rows.py (Dateigrößenlimit). Nutzt dieselbe Port-Grundlage über
die Modulreferenz (`from . import crypto_bridge` + `crypto_bridge._load_port()`,
NICHT `from .crypto_bridge import _load_port` - sonst greift der monkeypatch
in den Tests nicht).

Drei Gruppen, household-weit (kein Portfolio/Wallet-Parameter nötig - jedes
verknüpfte Konto des Users wird über seine Chain gefunden, crypto_ledger_rows):
- Swap: Transfer-Zeile Von-Konto -> Nach-Konto (counter_account_id), NIE
  Einnahme/Ausgabe.
- Kartenzahlung/Abgang: Ausgabe-Zeile vom jeweiligen Krypto-Konto
  (row_account_id), Kategorie optional (Till weist sie zu - import_completion
  bucht das Gegenposting ohne Kategorie auf "Ohne Kategorie").
  Abgang-Zeilen werden nach dem Einfügen auf status='rejected' gesetzt -
  standardmäßig ausgeschlossen (Till entscheidet, Zieldokument §6 Punkt 4).
- Unklar (fehlendes Swap-Bein, kein eindeutiges Konto, value_minor None,
  unbekannter Typ): Zeile mit Fehlercode, nicht buchbar.

Dedup: stabile Kennung = ledger_moves-Eintrag.id als bank_reference/
Fingerprint (import_inbox.insert_import_rows dedupt automatisch über den
bestehenden Fingerprint-Mechanismus); ein zweiter Aufruf liefert dieselben
Zeilen als 'duplicate' zurück, 0 neue buchbare.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import replace

from fastapi import status
from hydrahive.api.middleware.auth import AuthPrincipal
from hydrahive.api.middleware.errors import coded
from hydrahive.db.connection import db

from . import audit, crypto_bridge
from .access import membership
from .crypto_bridge import CryptoBridgeUnavailable, _CRYPTO_CURRENCY
from .crypto_ledger_rows import classify_move, unklar_record
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


def _own_accounts(conn, household_id: int, user_id: str) -> list[int]:
    rows = conn.execute(
        "SELECT DISTINCT account_id FROM module_haushaltsbuch_account_crypto_addresses "
        "WHERE household_id=? AND linked_user_id=?",
        (household_id, user_id),
    ).fetchall()
    return [row["account_id"] for row in rows]


def _load_ledger_port(principal: AuthPrincipal):
    try:
        port = crypto_bridge._load_port()
    except CryptoBridgeUnavailable as exc:
        raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "crypto_bridge_unavailable", reason=exc.reason) from exc
    if not hasattr(port, "ledger_moves"):
        raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "crypto_bridge_unavailable", reason="port_incompatible")
    try:
        return port.ledger_moves(principal.username, limit=_LEDGER_LIMIT)
    except port.PortfolioUnavailable as exc:
        raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "crypto_bridge_unavailable", reason="portfolio_unavailable") from exc


def _insert_rows(
    conn, household_id: int, batch_id: int, batch_account_id: int,
    groups_source: dict[str, list[dict]], unklar: list[dict],
) -> list[str]:
    """Fügt alle Zeilen ein (je Zielkonto gruppiert) und markiert Abgänge als
    'rejected'. Gibt die bank_reference der Abgang-Zeilen zurück."""
    source_line = 0
    abgang_refs: list[str] = []
    for group_name, items in groups_source.items():
        by_account: dict[int, list[NormalizedRecord]] = {}
        for item in items:
            source_line += 1
            by_account.setdefault(item["account_id"], []).append(replace(item["record"], source_line=source_line))
            if group_name == "abgang":
                abgang_refs.append(item["record"].bank_reference)
        for account_id, records in by_account.items():
            insert_import_rows(conn, household_id, batch_id, account_id, _CRYPTO_CURRENCY, records)
    unklar_records = [unklar_record(source_line + i + 1, item) for i, item in enumerate(unklar)]
    if unklar_records:
        insert_import_rows(conn, household_id, batch_id, batch_account_id, _CRYPTO_CURRENCY, unklar_records)
    return abgang_refs


def preview_ledger_import(principal: AuthPrincipal) -> dict:
    """POST /crypto-bridge/ledger-imports - household-weit, kein Portfolio-
    Parameter nötig. Legt einen Draft-Batch im bestehenden Prüfbereich an
    (wie POST /imports), ohne irgendetwas zu buchen."""
    with db(immediate=True) as conn:
        member = membership(conn, principal)
        household_id = member["household_id"]
        own_account_ids = _own_accounts(conn, household_id, principal.user_id)
        if not own_account_ids:
            raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "crypto_wallet_not_linked")
        batch_account_id = min(own_account_ids)

        moves = _load_ledger_port(principal)

        classified = [classify_move(conn, household_id, principal.user_id, move) for move in moves]
        groups_source: dict[str, list[dict]] = {"swap": [], "kartenzahlung": [], "abgang": []}
        unklar: list[dict] = []
        for item in classified:
            if item["group"] == "unklar":
                unklar.append({"id": item.get("id"), "reason": item["reason"]})
            else:
                groups_source[item["group"]].append(item)

        if not any(groups_source.values()) and not unklar:
            raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "no_records")

        file_hash = _random_file_hash()
        cursor = conn.execute(
            "INSERT INTO module_haushaltsbuch_import_batches"
            "(household_id,account_id,display_filename,source_format,file_hash,created_by) VALUES(?,?,?,?,?,?)",
            (household_id, batch_account_id, "Cryptoboard-Ledger", "crypto_ledger", file_hash, principal.user_id),
        )
        batch_id = int(cursor.lastrowid)

        abgang_refs = _insert_rows(conn, household_id, batch_id, batch_account_id, groups_source, unklar)

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
