"""On-Chain-Import — reine Format-Helfer (Entry/Hash/Zeit/Decimal-String).

Ausgelagert aus onchain_import.py (Datei-Größenlimit ~200 Zeilen): keine
Logik-Änderung, nur Verschiebung. Wird von onchain_import.py UND
onchain_preview_all.py genutzt (gemeinsame Entry-Form für Swaps/Ausgaben).
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from . import onchain_swaps as sw

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


def qty(side: dict) -> Decimal:
    return Decimal(int(side["amount_base_units"])) / (Decimal(10) ** int(side["decimals"]))


def direction(address: str, t: dict) -> str:
    a = address.lower()
    if str(t.get("from") or "").lower() == a:
        return "raus"
    if str(t.get("to") or "").lower() == a:
        return "rein"
    return "fremd"


def compact_unklar(chain: str, address: str, item: dict) -> dict:
    tokens = []
    for t in (item.get("raw") or [])[:_MAX_RAW_TOKENS]:
        raw = t.get("rawContract") or {}
        amount = sw.decimal_amount(t, chain) if sw._raw_amount(t, chain)[1] is not None else None
        tokens.append({
            "symbol": str(raw.get("symbol") or t.get("asset") or "?"),
            "contract": raw.get("address"),
            "category": t.get("category"),
            "direction": direction(address, t),
            "amount": dec_str(amount),
        })
    return {"hash": item.get("hash"), "chain": chain, "executed_at": normalize_ts(item.get("executed_at")),
            "reason": item.get("reason"), "tokens": tokens}


def compact_wrap(item: dict) -> dict:
    assets = []
    for mv in (item.get("assets") or {}).values():
        net = int(mv["net"])
        amount = Decimal(abs(net)) / (Decimal(10) ** int(mv["decimals"] or 0))
        assets.append({"symbol": mv.get("symbol"), "contract": mv.get("contract"),
                       "direction": "raus" if net < 0 else "rein", "amount": dec_str(amount)})
    return {"hash": item.get("hash"), "executed_at": normalize_ts(item.get("executed_at")), "assets": assets}


def build_entry(chain: str, swap: dict, kind: str, res: dict, quantity: Decimal, price: Decimal | None,
                 fee: Decimal | None, flags: list[str]) -> dict:
    side = swap[kind]
    return {
        "hash": import_hash(chain, swap["hash"], kind),
        "tx_hash": swap["hash"].lower(),
        "coin_id": res["coin_id"],
        "symbol": str(side.get("symbol") or "").upper()[:20],
        "name": (res.get("name") or "")[:120],
        "kind": kind,
        "quantity": dec_str(quantity),
        "price": dec_str(price),
        "fee": dec_str(fee),
        "executed_at": normalize_ts(swap.get("executed_at")),
        "resolved": not res["unresolved"],
        "preis_fehlt": "preis_fehlt" in flags,
        "gebuehr_fehlt": "gebuehr_fehlt" in flags,
        "duplicate": False,
    }
