"""Swap-Erkennung über Token-Bewegungen — reine Funktionen, kein Netzzugriff.

Regel (Till, 2026-11-19): Transfers nach Tx-Hash gruppieren, je Asset die
Netto-Bewegung relativ zur betrachteten Adresse bilden (negativ = Adresse
ist from, positiv = Adresse ist to). Genau 1 Asset netto raus + genau 1
ANDERES Asset netto rein → Swap (sell(A) + buy(B)). Alles andere (nur eine
Richtung, mehrere Assets je Seite, Approve ohne Transfer) → "unklar" mit
Rohdaten, NIE geraten.

WETH<->ETH (Wrap/Unwrap) ist kein Trade (kein Kursereignis) — eigener
Hinweistyp.

Mengen werden ausschließlich aus rawContract.value (Hex) + rawContract.decimal
als Integer-Basiseinheiten (int) bzw. Decimal gebildet — NICHT aus dem
gerundeten Float-Feld "value" (rundet bei vielen Dezimalstellen/großen
Beträgen falsch).

Noch OHNE Preis-/coin_id-Auflösung (Teil B) — Ausgabe enthält Kontraktadresse/
Symbol/decimals, damit Teil B die Auflösung ergänzen kann.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

_WETH_CONTRACTS = {
    "base": "0x4200000000000000000000000000000000000006",
    "ethereum": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
}
_NATIVE_ASSET_KEY = "__native__"


def _asset_key(transfer: dict) -> str:
    """Stabiler Schlüssel je Asset: Contract-Adresse (klein) für ERC20, sonst Symbol."""
    raw = transfer.get("rawContract") or {}
    contract = raw.get("address")
    if contract:
        return str(contract).lower()
    return _NATIVE_ASSET_KEY if transfer.get("category") == "external" else str(transfer.get("asset") or "?")


def _raw_amount(transfer: dict) -> tuple[int, int]:
    """(Integer-Basiseinheiten, decimals) exakt aus rawContract.value (Hex) + .decimal.

    NIE aus dem Float-Feld "value" — das rundet bei 18 Dezimalen/großen
    Beträgen bereits bei der Alchemy-Antwort selbst.
    """
    raw = transfer.get("rawContract") or {}
    value_hex = raw.get("value")
    decimals_raw = raw.get("decimal")
    if value_hex is None:
        return 0, 0
    try:
        amount = int(str(value_hex), 16)
    except (TypeError, ValueError):
        return 0, 0
    try:
        decimals = int(str(decimals_raw), 16) if isinstance(decimals_raw, str) and decimals_raw.startswith("0x") \
            else int(decimals_raw)
    except (TypeError, ValueError):
        decimals = 0
    return amount, decimals


def decimal_amount(transfer: dict) -> Decimal:
    """Menge als Decimal (Basiseinheiten / 10**decimals) — für Anzeige/Tests."""
    amount, decimals = _raw_amount(transfer)
    if amount == 0:
        return Decimal(0)
    return Decimal(amount) / (Decimal(10) ** decimals)


def _symbol(transfer: dict) -> str:
    raw = transfer.get("rawContract") or {}
    return str(raw.get("symbol") or transfer.get("asset") or "?")


def _is_weth_wrap_pair(chain: str, keys: set[str]) -> bool:
    weth = _WETH_CONTRACTS.get(chain, "").lower()
    return keys == {weth, _NATIVE_ASSET_KEY}


def group_by_hash(transfers: list[dict]) -> dict[str, list[dict]]:
    """Transfers nach Tx-Hash gruppiert, Reihenfolge der ersten Sichtung erhalten."""
    out: dict[str, list[dict]] = {}
    for t in transfers:
        h = t.get("hash")
        if not h:
            continue
        out.setdefault(h, []).append(t)
    return out


def _net_movements(address: str, txs: list[dict]) -> dict[str, dict[str, Any]]:
    """Je Asset: Netto-Basiseinheiten relativ zur Adresse + Metadaten (decimals/symbol/contract)."""
    address_lower = address.lower()
    movements: dict[str, dict[str, Any]] = {}
    for t in txs:
        amount, decimals = _raw_amount(t)
        if amount == 0:
            continue
        key = _asset_key(t)
        slot = movements.setdefault(key, {
            "net": 0, "decimals": decimals, "symbol": _symbol(t),
            "contract": (t.get("rawContract") or {}).get("address"),
        })
        frm = str(t.get("from") or "").lower()
        to = str(t.get("to") or "").lower()
        if frm == address_lower:
            slot["net"] -= amount
        if to == address_lower:
            slot["net"] += amount
    return {k: v for k, v in movements.items() if v["net"] != 0}


def classify_transaction(chain: str, address: str, tx_hash: str, txs: list[dict]) -> dict:
    """Ein Tx-Hash -> {"type": "swap"|"wrap"|"unklar", ...}. Reine Funktion, kein Raten."""
    movements = _net_movements(address, txs)
    executed_at = (txs[0].get("metadata") or {}).get("blockTimestamp") if txs else None
    base = {"hash": tx_hash, "chain": chain, "executed_at": executed_at}

    if not movements:
        return {**base, "type": "unklar", "reason": "keine_nettobewegung", "raw": txs}

    if _is_weth_wrap_pair(chain, set(movements)):
        return {**base, "type": "wrap", "assets": movements}

    out_assets = {k: v for k, v in movements.items() if v["net"] < 0}
    in_assets = {k: v for k, v in movements.items() if v["net"] > 0}

    if len(out_assets) != 1 or len(in_assets) != 1:
        return {**base, "type": "unklar", "reason": "mehrdeutige_bewegung", "raw": txs,
                "out_assets": out_assets, "in_assets": in_assets}

    (sell_key, sell), = out_assets.items()
    (buy_key, buy), = in_assets.items()
    return {
        **base, "type": "swap",
        "sell": {"contract": sell["contract"], "symbol": sell["symbol"],
                  "decimals": sell["decimals"], "amount_base_units": -sell["net"]},
        "buy": {"contract": buy["contract"], "symbol": buy["symbol"],
                 "decimals": buy["decimals"], "amount_base_units": buy["net"]},
    }


def detect_swaps(chain: str, address: str, transfers: list[dict]) -> dict:
    """Haupteinstieg: Transfer-Liste -> {"swaps": [...], "wraps": [...], "unklar": [...]}."""
    grouped = group_by_hash(transfers)
    swaps: list[dict] = []
    wraps: list[dict] = []
    unklar: list[dict] = []
    for tx_hash, txs in grouped.items():
        result = classify_transaction(chain, address, tx_hash, txs)
        if result["type"] == "swap":
            swaps.append(result)
        elif result["type"] == "wrap":
            wraps.append(result)
        else:
            unklar.append(result)
    return {"swaps": swaps, "wraps": wraps, "unklar": unklar}
