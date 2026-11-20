"""Read-Port v3 — Ledger-Bewegungen für das Haushaltsbuch (VERTRAG-B.md Punkt 3).

ledger_moves(username) liest NUR On-Chain-Import-Einträge (gültiger
import_hash laut onchain_rules.HASH_RE/XCHAIN_HASH_RE) aus dem bestehenden
Ledger (portfolio_store) und baut daraus zwei Bewegungsarten:

  Swap   — sell+buy mit identischem xchain-Präfix "xchain:{tron_tx}:
           {evm_chain}:{evm_tx}" (Paarung NUR über den Hash, kein Zeitfenster-
           Raten). Fehlt ein Bein (nur sell ODER nur buy desselben Präfixes
           vorhanden) -> eigener "unklar"-Eintrag (reason swap_bein_fehlt),
           NIE als Swap gezeigt.
  Zahlung — transfer_out mit Hash "{chain}:{tx}:transfer_out". art kommt
           aus der note (siehe onchain_import.NOTE_KARTENZAHLUNG/NOTE_ABGANG);
           jede andere/fehlende note gilt als "abgang" (kein Raten – sicherer
           Default, wie die Vorschau selbst).

Ausgelagert aus read_port.py (Datei-Größenlimit ~200 Zeilen); read_port.py
re-exportiert ledger_moves, bleibt EINE Einstiegsdatei für andere Module.
"""
from __future__ import annotations

from . import onchain_import as oi
from . import portfolio_store as store
from .onchain_rules import HASH_RE, XCHAIN_HASH_RE


def _xchain_prefix(import_hash: str) -> str | None:
    """"xchain:{tron_tx}:{evm_chain}:{evm_tx}:sell|buy" -> "xchain:{tron_tx}:{evm_chain}:{evm_tx}"."""
    parts = import_hash.split(":")
    return ":".join(parts[:-1]) if len(parts) == 5 else None


def _evm_chain_of(import_hash: str) -> str:
    """EVM-Chain eines Beins aus seinem import_hash ("xchain:{tron_tx}:{chain}:{evm_tx}:sell|buy")."""
    parts = import_hash.split(":")
    return parts[2] if len(parts) == 5 else ""


def _leg(row: dict, chain: str, *, to_minor, quantity_str) -> dict:
    return {
        "chain": chain, "symbol": row["symbol"], "coin_id": row["coin_id"],
        "quantity": quantity_str(row["quantity"]),
        "gross_minor": to_minor(row["quantity"] * (row["price"] or 0.0)), "ref": f"cb:{row['id']}",
    }


def _swap_entries(legs: dict[str, dict[str, dict]], *, to_minor, quantity_str) -> list[dict]:
    """legs: {prefix: {"sell": row|None, "buy": row|None}} -> Swap- oder Unklar-Einträge."""
    out: list[dict] = []
    for prefix, sides in legs.items():
        sell, buy = sides.get("sell"), sides.get("buy")
        if sell is None or buy is None:
            present = sell or buy
            out.append({
                "type": "unklar", "reason": "swap_bein_fehlt", "id": prefix,
                "executed_at": present["executed_at"] if present else None,
                "ref": f"cb:{present['id']}" if present else None,
            })
            continue
        from_leg = _leg(sell, "tron", to_minor=to_minor, quantity_str=quantity_str)
        from_leg["fee_minor"] = to_minor(sell["fee"] or 0.0)
        to_leg = _leg(buy, _evm_chain_of(buy["import_hash"]), to_minor=to_minor, quantity_str=quantity_str)
        out.append({
            "type": "swap", "id": prefix, "executed_at": buy["executed_at"],
            "from": from_leg, "to": to_leg, "value_minor": to_leg["gross_minor"],
        })
    return out


def _payment_art(note: str) -> str:
    if note == oi.NOTE_KARTENZAHLUNG:
        return "kartenzahlung"
    return "abgang"  # unbekannte/fehlende note -> sicherer Default, kein Raten einer anderen Art


def _payment_entry(row: dict, *, to_minor, quantity_str) -> dict:
    chain = row["import_hash"].split(":")[0]
    value_minor = to_minor(row["quantity"] * row["price"]) if row["price"] else None
    return {
        "type": _payment_art(row["note"]), "id": row["import_hash"], "executed_at": row["executed_at"],
        "chain": chain, "symbol": row["symbol"], "coin_id": row["coin_id"],
        "quantity": quantity_str(row["quantity"]), "value_minor": value_minor, "ref": f"cb:{row['id']}",
    }


def ledger_moves(username: str, *, since: str | None = None, limit: int = 5000,
                  to_minor, quantity_str) -> list[dict]:
    """Haupteinstieg: Ledger -> Liste von Swap-/Zahlungs-/Unklar-Bewegungen, chronologisch.

    `to_minor`/`quantity_str` werden von read_port.py durchgereicht (einzige
    Rundungsregel bleibt dort). Nur Zeilen mit gültigem On-Chain-Import-Hash
    zählen; alles andere (CSV-Import, manuelle Einträge) wird ignoriert —
    dieser Port zeigt ausschließlich On-Chain-Bewegungen.
    """
    rows = store.list_for(username)
    if since:
        rows = [r for r in rows if str(r.get("executed_at") or "") >= since]

    legs: dict[str, dict[str, dict]] = {}
    moves: list[dict] = []
    for row in rows:
        import_hash = row.get("import_hash") or ""
        m = XCHAIN_HASH_RE.match(import_hash)
        if m:
            prefix = _xchain_prefix(import_hash)
            kind = "sell" if import_hash.endswith(":sell") else "buy"
            legs.setdefault(prefix, {})[kind] = row
            continue
        hm = HASH_RE.match(import_hash)
        if hm and import_hash.endswith(":transfer_out"):
            moves.append(_payment_entry(row, to_minor=to_minor, quantity_str=quantity_str))

    moves.extend(_swap_entries(legs, to_minor=to_minor, quantity_str=quantity_str))
    moves.sort(key=lambda m: str(m.get("executed_at") or ""))
    return moves[:limit] if limit is not None else moves
