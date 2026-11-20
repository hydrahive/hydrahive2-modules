"""On-Chain-Import — Preview-Aufbau (Swaps → buy/sell-Vorschläge) und Commit-Logik.

Ablauf Preview: fetch_transfers → detect_swaps → resolve_coin_id je Seite →
ensure_prices_cached → price_pair → sell_side_fee. Je Swap zwei Einträge
(sell + buy) mit import_hash "{chain}:{txhash}:sell|buy".

Zahlen: intern Decimal; in der Preview als exakte Strings (quantity/price/fee);
die einzige Umwandlung nach float (Ledger ist REAL) passiert in commit_entries
direkt vor store.add. Nichts wird geraten: kein Kurs → price None + preis_fehlt,
keine Gebühr ermittelbar → fee None + gebuehr_fehlt.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from . import alchemy_client as ac
from . import onchain_gas as gas
from . import onchain_resolve as rs
from . import onchain_swaps as sw
from . import portfolio_store as store
from .onchain_rules import HASH_RE, XCHAIN_HASH_RE, mark_bookable, skip_reason
from .onchain_entries import (
    build_entry, compact_unklar, compact_wrap, dec_str, direction, import_hash, normalize_ts, qty,
)

NOTE = "On-Chain-Import"
NOTE_KARTENZAHLUNG = "On-Chain-Import Kartenzahlung"
NOTE_ABGANG = "On-Chain-Import Abgang"
CHAINS = ("base", "ethereum")
# Zwei Hash-Formate laut VERTRAG.md:
#   base/ethereum:tx:sell|buy|transfer_out   — Swap/Ausgabe innerhalb einer Chain
#   xchain:tron_tx:evm_chain:evm_tx:sell|buy — chain-übergreifendes Paar

__all__ = [
    "CHAINS", "HASH_RE", "NOTE", "NOTE_ABGANG", "NOTE_KARTENZAHLUNG", "XCHAIN_HASH_RE", "build_entry",
    "build_preview", "commit_entries", "compact_unklar", "compact_wrap", "dec_str", "direction",
    "import_hash", "normalize_ts", "process_swaps", "qty",
]


async def process_swaps(chain: str, address: str, key: str, detected: dict, grouped: dict,
                         *, extra_needed: dict[str, str | None] | None = None) -> tuple[list[dict], bool]:
    """Erkannte Swaps einer Adresse -> (entries, kurs_abruf_fehlgeschlagen).

    Gemeinsamer Kern von build_preview (Einzel-Adresse) und
    onchain_preview_all.preview_all (alle Adressen) — Preis-/Gas-Logik lebt
    nur HIER, damit beide Aufrufer identisch rechnen. `extra_needed` erlaubt
    preview_all, zusätzliche coin_ids (z. B. "tron" für die Pairing-Gebühr)
    in denselben Kurs-Vorlauf aufzunehmen (ein CoinGecko-Abruf je Coin/Lauf).
    """
    resolved: list[tuple[dict, dict, dict]] = []
    for swap in detected["swaps"]:
        r_sell = await rs.resolve_coin_id(chain, swap["sell"]["contract"], swap["sell"]["symbol"])
        r_buy = await rs.resolve_coin_id(chain, swap["buy"]["contract"], swap["buy"]["symbol"])
        resolved.append((swap, r_sell, r_buy))

    needed: dict[str, str | None] = dict(extra_needed or {})
    for swap, a, b in resolved:
        day = rs.day_of(swap.get("executed_at"))
        for coin_id in [r["coin_id"] for r in (a, b) if r["coin_id"]] + ["ethereum"]:  # ethereum: Gas-Umrechnung
            prev = needed.get(coin_id)
            needed[coin_id] = day if prev is None or (day is not None and day > prev) else prev
    kurs_abruf_fehlgeschlagen = False
    try:
        await rs.ensure_prices_cached(needed)
    except Exception:  # CoinGecko-Fehler → fehlende Kurse werden als preis_fehlt markiert
        kurs_abruf_fehlgeschlagen = True

    entries: list[dict] = []
    receipts_used = 0
    for swap, r_sell, r_buy in resolved:
        day = rs.day_of(swap.get("executed_at"))
        q_sell, q_buy = qty(swap["sell"]), qty(swap["buy"])
        p_sell, p_buy, _ = rs.price_pair(r_sell["coin_id"], q_sell, r_buy["coin_id"], q_buy, day)
        fee, gebuehr_fehlt, receipts_used = await gas.sell_side_fee(
            chain, key, address, swap["hash"], grouped.get(swap["hash"], []), day, receipts_used=receipts_used)
        sell_flags = (["preis_fehlt"] if p_sell is None else []) + (["gebuehr_fehlt"] if gebuehr_fehlt else [])
        buy_flags = ["preis_fehlt"] if p_buy is None else []
        entries.append(build_entry(chain, swap, "sell", r_sell, q_sell, p_sell, fee, sell_flags))
        entries.append(build_entry(chain, swap, "buy", r_buy, q_buy, p_buy, Decimal(0), buy_flags))
    return entries, kurs_abruf_fehlgeschlagen


async def build_preview(user: str, chain: str, address: str, key: str, to_block: str | None) -> dict:
    """Alchemy-Fehler (ac.*) laufen bewusst nach oben — die Route mappt sie auf Codes."""
    fetched = await ac.fetch_transfers(chain, key, address, to_block=to_block or "latest")
    transfers = fetched["transfers"]
    detected = sw.detect_swaps(chain, address, transfers)
    grouped = sw.group_by_hash(transfers)

    entries, kurs_abruf_fehlgeschlagen = await process_swaps(chain, address, key, detected, grouped)

    mark_bookable(entries, store.existing_hashes(user, [e["hash"] for e in entries]))

    return {
        "chain": chain,
        "address": address,
        "transactions": entries,
        "wraps": [compact_wrap(w) for w in detected["wraps"]],
        "unklar": [compact_unklar(chain, address, u) for u in detected["unklar"]],
        "truncated": bool(fetched.get("truncated")),
        "before_block": fetched.get("before_block"),
        "kurs_abruf_fehlgeschlagen": kurs_abruf_fehlgeschlagen,
        "counts": {
            "swaps": len(detected["swaps"]),
            "transactions": len(entries),
            "wraps": len(detected["wraps"]),
            "unklar": len(detected["unklar"]),
            "duplicates": sum(1 for e in entries if e["duplicate"]),
            "preis_fehlt": sum(1 for e in entries if e["preis_fehlt"]),
            "gebuehr_fehlt": sum(1 for e in entries if e["gebuehr_fehlt"]),
            "unresolved": sum(1 for e in entries if not e["resolved"]),
        },
    }


def _note_for(t: Any) -> str:
    """note je Eintrag: transfer_out unterscheidet Kartenzahlung/Abgang (VERTRAG-B.md Punkt 2),
    buy/sell (Swaps) bleiben bei der bisherigen generischen note."""
    if getattr(t, "kind", None) != "transfer_out":
        return NOTE
    art = getattr(t, "art", None)
    return NOTE_KARTENZAHLUNG if art == "kartenzahlung" else NOTE_ABGANG


def commit_entries(user: str, transactions: list[Any]) -> dict:
    """Bestätigte Einträge ins Ledger — Dedup über existing_hashes + innerhalb des Requests."""
    already = store.existing_hashes(user, [t.hash for t in transactions])
    imported = 0
    details: list[dict] = []
    for t in transactions:
        reason = skip_reason(t, already)
        if reason is None:
            fee = t.fee if t.fee is not None else Decimal(0)
            price = t.price if t.price is not None else Decimal(0)  # transfer_out ohne Preis -> 0
            try:
                # EINZIGE Decimal→float-Grenze: das Ledger speichert REAL.
                store.add(
                    user, coin_id=t.coin_id.strip().lower(), symbol=t.symbol.strip().upper(),
                    name=t.name.strip(), kind=t.kind, quantity=float(t.quantity),
                    price=float(price), fee=float(fee), executed_at=t.executed_at.strip(),
                    note=_note_for(t), import_hash=t.hash,
                )
                imported += 1
                already.add(t.hash)
                continue
            except ValueError as exc:
                reason = str(exc) if str(exc) == "ledger_full" else "ungueltig"
        details.append({"hash": t.hash, "reason": reason})
    return {"ok": True, "imported": imported, "skipped": len(details), "skipped_details": details}
