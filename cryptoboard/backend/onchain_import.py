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

import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from . import alchemy_client as ac
from . import onchain_gas as gas
from . import onchain_resolve as rs
from . import onchain_swaps as sw
from . import portfolio_store as store
from .validators import ID_RE, ISO_RE

NOTE = "On-Chain-Import"
CHAINS = ("base", "ethereum")
HASH_RE = re.compile(r"^(base|ethereum):0x[0-9a-f]{64}:(sell|buy)$")
_MAX_RAW_TOKENS = 20


def import_hash(chain: str, tx_hash: str, kind: str) -> str:
    return f"{chain}:{tx_hash.lower()}:{kind}"


def dec_str(value: Decimal | None) -> str | None:
    """Decimal → exakter String ohne Exponent ('1000', '0.000001')."""
    if value is None:
        return None
    s = format(value, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s or "0"


def normalize_ts(ts: str | None) -> str | None:
    """Alchemy-blockTimestamp ('…T12:00:00.000Z') → 'YYYY-MM-DDTHH:MM:SSZ' (UTC)."""
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _qty(side: dict) -> Decimal:
    return Decimal(int(side["amount_base_units"])) / (Decimal(10) ** int(side["decimals"]))


def _direction(address: str, t: dict) -> str:
    a = address.lower()
    if str(t.get("from") or "").lower() == a:
        return "raus"
    if str(t.get("to") or "").lower() == a:
        return "rein"
    return "fremd"


def _compact_unklar(chain: str, address: str, item: dict) -> dict:
    tokens = []
    for t in (item.get("raw") or [])[:_MAX_RAW_TOKENS]:
        raw = t.get("rawContract") or {}
        amount = sw.decimal_amount(t, chain) if sw._raw_amount(t, chain)[1] is not None else None
        tokens.append({
            "symbol": str(raw.get("symbol") or t.get("asset") or "?"),
            "contract": raw.get("address"),
            "category": t.get("category"),
            "direction": _direction(address, t),
            "amount": dec_str(amount),
        })
    return {"hash": item.get("hash"), "executed_at": normalize_ts(item.get("executed_at")),
            "reason": item.get("reason"), "tokens": tokens}


def _compact_wrap(item: dict) -> dict:
    assets = []
    for mv in (item.get("assets") or {}).values():
        net = int(mv["net"])
        amount = Decimal(abs(net)) / (Decimal(10) ** int(mv["decimals"] or 0))
        assets.append({"symbol": mv.get("symbol"), "contract": mv.get("contract"),
                       "direction": "raus" if net < 0 else "rein", "amount": dec_str(amount)})
    return {"hash": item.get("hash"), "executed_at": normalize_ts(item.get("executed_at")), "assets": assets}


def _entry(chain: str, swap: dict, kind: str, res: dict, qty: Decimal, price: Decimal | None,
           fee: Decimal | None, flags: list[str]) -> dict:
    side = swap[kind]
    return {
        "hash": import_hash(chain, swap["hash"], kind),
        "tx_hash": swap["hash"].lower(),
        "coin_id": res["coin_id"],
        "symbol": str(side.get("symbol") or "").upper()[:20],
        "name": (res.get("name") or "")[:120],
        "kind": kind,
        "quantity": dec_str(qty),
        "price": dec_str(price),
        "fee": dec_str(fee),
        "executed_at": normalize_ts(swap.get("executed_at")),
        "resolved": not res["unresolved"],
        "preis_fehlt": "preis_fehlt" in flags,
        "gebuehr_fehlt": "gebuehr_fehlt" in flags,
        "duplicate": False,
    }


async def build_preview(user: str, chain: str, address: str, key: str, to_block: str | None) -> dict:
    """Alchemy-Fehler (ac.*) laufen bewusst nach oben — die Route mappt sie auf Codes."""
    fetched = await ac.fetch_transfers(chain, key, address, to_block=to_block or "latest")
    transfers = fetched["transfers"]
    detected = sw.detect_swaps(chain, address, transfers)
    grouped = sw.group_by_hash(transfers)

    resolved: list[tuple[dict, dict, dict]] = []
    for swap in detected["swaps"]:
        r_sell = await rs.resolve_coin_id(chain, swap["sell"]["contract"], swap["sell"]["symbol"])
        r_buy = await rs.resolve_coin_id(chain, swap["buy"]["contract"], swap["buy"]["symbol"])
        resolved.append((swap, r_sell, r_buy))

    needed: dict[str, str | None] = {}  # coin_id → jüngster Swap-Tag (Cache muss mindestens bis dahin reichen)
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
        q_sell, q_buy = _qty(swap["sell"]), _qty(swap["buy"])
        p_sell, p_buy, _ = rs.price_pair(r_sell["coin_id"], q_sell, r_buy["coin_id"], q_buy, day)
        fee, gebuehr_fehlt, receipts_used = await gas.sell_side_fee(
            chain, key, address, swap["hash"], grouped.get(swap["hash"], []), day, receipts_used=receipts_used)
        sell_flags = (["preis_fehlt"] if p_sell is None else []) + (["gebuehr_fehlt"] if gebuehr_fehlt else [])
        buy_flags = ["preis_fehlt"] if p_buy is None else []
        entries.append(_entry(chain, swap, "sell", r_sell, q_sell, p_sell, fee, sell_flags))
        entries.append(_entry(chain, swap, "buy", r_buy, q_buy, p_buy, Decimal(0), buy_flags))

    already = store.existing_hashes(user, [e["hash"] for e in entries])
    for e in entries:
        e["duplicate"] = e["hash"] in already

    return {
        "chain": chain,
        "address": address,
        "transactions": entries,
        "wraps": [_compact_wrap(w) for w in detected["wraps"]],
        "unklar": [_compact_unklar(chain, address, u) for u in detected["unklar"]],
        "truncated": bool(fetched.get("truncated")),
        "before_block": fetched.get("before_block"),
        "kurs_abruf_fehlgeschlagen": kurs_abruf_fehlgeschlagen,
        "counts": {
            "swaps": len(resolved),
            "transactions": len(entries),
            "wraps": len(detected["wraps"]),
            "unklar": len(detected["unklar"]),
            "duplicates": sum(1 for e in entries if e["duplicate"]),
            "preis_fehlt": sum(1 for e in entries if e["preis_fehlt"]),
            "gebuehr_fehlt": sum(1 for e in entries if e["gebuehr_fehlt"]),
            "unresolved": sum(1 for e in entries if not e["resolved"]),
        },
    }


def _skip_reason(t: Any, already: set[str]) -> str | None:
    if not HASH_RE.match(t.hash) or not t.hash.endswith(f":{t.kind}"):
        return "hash_ungueltig"
    if t.hash in already:
        return "duplikat"
    if not t.coin_id or not ID_RE.match(t.coin_id.strip().lower()):
        return "coin_id_fehlt"
    if t.price is None:
        return "preis_fehlt"
    if not ISO_RE.match(t.executed_at.strip()):
        return "zeit_ungueltig"
    return None


def commit_entries(user: str, transactions: list[Any]) -> dict:
    """Bestätigte Einträge ins Ledger — Dedup über existing_hashes + innerhalb des Requests."""
    already = store.existing_hashes(user, [t.hash for t in transactions])
    imported = 0
    details: list[dict] = []
    for t in transactions:
        reason = _skip_reason(t, already)
        if reason is None:
            fee = t.fee if t.fee is not None else Decimal(0)
            try:
                # EINZIGE Decimal→float-Grenze: das Ledger speichert REAL.
                store.add(
                    user, coin_id=t.coin_id.strip().lower(), symbol=t.symbol.strip().upper(),
                    name=t.name.strip(), kind=t.kind, quantity=float(t.quantity),
                    price=float(t.price), fee=float(fee), executed_at=t.executed_at.strip(),
                    note=NOTE, import_hash=t.hash,
                )
                imported += 1
                already.add(t.hash)
                continue
            except ValueError as exc:
                reason = str(exc) if str(exc) == "ledger_full" else "ungueltig"
        details.append({"hash": t.hash, "reason": reason})
    return {"ok": True, "imported": imported, "skipped": len(details), "skipped_details": details}
