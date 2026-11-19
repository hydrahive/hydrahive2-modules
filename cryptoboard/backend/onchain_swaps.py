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

Korrekturen aus dem Review (Teil B, 2026-11-19):
  K1 — natives ETH kommt bei Alchemy auch als category "internal" ohne
       rawContract.address vor (z. B. Unwrap-Refund, Router zahlt ETH aus).
       Nicht nur "external" gilt als nativ, sonst wird ein Unwrap als Swap
       WETH->ETH fehlinterpretiert bzw. ein Swap mit internem Refund als
       "unklar" (zwei vermeintliche Assets statt eines).
  K2 — fehlende/ungültige decimals werden NICHT mehr still als 0 angenommen.
       decimals kommen aus rawContract.decimal, sonst aus der bekannten
       Token-Liste (chain_clients._EVM) anhand der Kontraktadresse. Bleiben
       sie unbekannt, wird die GANZE Transaktion "unklar" (reason
       "decimals_fehlt") statt mit einer geratenen Dezimalstelle weiterzulaufen.

Noch OHNE Preis-/coin_id-Auflösung (Teil B) — Ausgabe enthält Kontraktadresse/
Symbol/decimals, damit Teil B die Auflösung ergänzen kann.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from . import chain_clients

_NATIVE_ASSET_KEY = "__native__"
# K1: beide Kategorien liefern natives ETH ohne rawContract.address.
_NATIVE_CATEGORIES = ("external", "internal")


def _asset_key(transfer: dict) -> str:
    """Stabiler Schlüssel je Asset: Contract-Adresse (klein) für ERC20, sonst nativ/Symbol."""
    raw = transfer.get("rawContract") or {}
    contract = raw.get("address")
    if contract:
        return str(contract).lower()
    return _NATIVE_ASSET_KEY if transfer.get("category") in _NATIVE_CATEGORIES else str(transfer.get("asset") or "?")


def _parse_decimals(decimals_raw: Any) -> int | None:
    if decimals_raw is None:
        return None
    try:
        if isinstance(decimals_raw, str) and decimals_raw.startswith("0x"):
            return int(decimals_raw, 16)
        return int(decimals_raw)
    except (TypeError, ValueError):
        return None


def _known_decimals(chain: str, contract: str | None) -> int | None:
    """K2: decimals eines bekannten ERC20-Tokens über chain_clients.known_token
    nachschlagen, falls Alchemy sie nicht (oder ungültig) mitliefert. Native
    Coins laufen NICHT hierüber (die haben keinen contract, decimals kommen
    direkt von Alchemy)."""
    if not contract:
        return None
    info = chain_clients.known_token(chain, contract)
    return info[2] if info else None


def _raw_amount(transfer: dict, chain: str) -> tuple[int, int | None]:
    """(Integer-Basiseinheiten, decimals) exakt aus rawContract.value (Hex) + .decimal.

    NIE aus dem Float-Feld "value" — das rundet bei 18 Dezimalen/großen
    Beträgen bereits bei der Alchemy-Antwort selbst.

    decimals ist None, wenn weder rawContract.decimal gültig ist NOCH der
    Kontrakt in der bekannten Token-Liste steht (K2) — der Aufrufer MUSS
    diesen Fall als "unklar" behandeln, nie als 0 interpretieren.
    """
    raw = transfer.get("rawContract") or {}
    value_hex = raw.get("value")
    if value_hex is None:
        return 0, None
    try:
        amount = int(str(value_hex), 16)
    except (TypeError, ValueError):
        return 0, None
    decimals = _parse_decimals(raw.get("decimal"))
    if decimals is None:
        decimals = _known_decimals(chain, raw.get("address"))
    return amount, decimals


def decimal_amount(transfer: dict, chain: str = "base") -> Decimal:
    """Menge als Decimal (Basiseinheiten / 10**decimals) — für Anzeige/Tests.

    `chain` wird nur für den K2-Fallback (bekannte Token-Decimals) gebraucht;
    Default "base" ist unschädlich, wenn rawContract.decimal bereits gültig ist.
    """
    amount, decimals = _raw_amount(transfer, chain)
    if amount == 0 or decimals is None:
        return Decimal(0)
    return Decimal(amount) / (Decimal(10) ** decimals)


def _symbol(transfer: dict) -> str:
    raw = transfer.get("rawContract") or {}
    return str(raw.get("symbol") or transfer.get("asset") or "?")


def _is_weth_wrap_pair(chain: str, keys: set[str]) -> bool:
    weth = chain_clients.WETH_CONTRACTS.get(chain, "").lower()
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


def _net_movements(chain: str, address: str, txs: list[dict]) -> tuple[dict[str, dict[str, Any]], bool]:
    """Je Asset: Netto-Basiseinheiten relativ zur Adresse + Metadaten (decimals/symbol/contract).

    K2: Zweiter Rückgabewert `decimals_missing` ist True, wenn IRGENDEIN
    beteiligter Transfer mit Netto-Bewegung != 0 keine bestimmbaren decimals
    hat — der Aufrufer macht daraus "unklar" statt eine Dezimalstelle zu raten.
    """
    address_lower = address.lower()
    movements: dict[str, dict[str, Any]] = {}
    decimals_missing = False
    for t in txs:
        amount, decimals = _raw_amount(t, chain)
        if amount == 0:
            continue
        frm = str(t.get("from") or "").lower()
        to = str(t.get("to") or "").lower()
        if frm != address_lower and to != address_lower:
            continue
        if decimals is None:
            decimals_missing = True
            continue
        key = _asset_key(t)
        slot = movements.setdefault(key, {
            "net": 0, "decimals": decimals, "symbol": _symbol(t),
            "contract": (t.get("rawContract") or {}).get("address"),
        })
        if frm == address_lower:
            slot["net"] -= amount
        if to == address_lower:
            slot["net"] += amount
    return {k: v for k, v in movements.items() if v["net"] != 0}, decimals_missing


def classify_transaction(chain: str, address: str, tx_hash: str, txs: list[dict]) -> dict:
    """Ein Tx-Hash -> {"type": "swap"|"wrap"|"unklar", ...}. Reine Funktion, kein Raten."""
    movements, decimals_missing = _net_movements(chain, address, txs)
    executed_at = (txs[0].get("metadata") or {}).get("blockTimestamp") if txs else None
    base = {"hash": tx_hash, "chain": chain, "executed_at": executed_at}

    if decimals_missing:
        return {**base, "type": "unklar", "reason": "decimals_fehlt", "raw": txs}

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
