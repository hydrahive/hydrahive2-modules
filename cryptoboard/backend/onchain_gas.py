"""Gas-Fee-Berechnung für On-Chain-Swaps (B3) — nur wenn die Adresse Absender ist.

Nur die SENDENDE Adresse zahlt Gas. Ermittelt wird das über:
  - Tx-from aus einem "external"/"internal"-Transfer der Tx (meistens vorhanden), ODER
  - eth_getTransactionByHash, falls nur erc20-Transfers vorliegen (ERC20-Transfer
    selbst trägt kein "from"-Feld der Tx, nur das Token-from/to).

Gebühr: eth_getTransactionReceipt -> gasUsed * effectiveGasPrice (Wei, exakt als
int), auf Base zusätzlich l1Fee falls vorhanden (Base ist ein L2, die L1-
Veröffentlichungsgebühr kommt separat dazu). Wei -> ETH -> EUR über den
ETH-Tageskurs (price_history-Cache, selbe Quelle wie B2).

Begrenzung: höchstens MAX_RECEIPTS_PER_RUN Receipts pro Lauf (Netz-Kosten).
Darüber hinaus bzw. bei jedem Fehler (Receipt nicht abrufbar, kein ETH-Kurs):
fee=None + flag "gebuehr_fehlt" — NIE ein Blocker, Commit mit fee=0 ist erlaubt.
"""
from __future__ import annotations

from decimal import Decimal

from . import alchemy_client as ac
from . import price_history_store as price_store

MAX_RECEIPTS_PER_RUN = 200


def _is_sender(address: str, txs: list[dict]) -> bool:
    """Tx-from aus einem nativen Transfer (external/internal) dieser Gruppe."""
    address_lower = address.lower()
    for t in txs:
        if t.get("category") in ("external", "internal"):
            if str(t.get("from") or "").lower() == address_lower:
                return True
    return False


async def _tx_from_via_hash(chain: str, key: str, tx_hash: str) -> str | None:
    """Fallback: nur erc20-Transfers vorhanden -> Tx-from per eth_getTransactionByHash."""
    try:
        result = await ac.call(chain, key, "eth_getTransactionByHash", [tx_hash])
    except Exception:
        return None
    if not isinstance(result, dict):
        return None
    frm = result.get("from")
    return str(frm).lower() if frm else None


async def is_sender(chain: str, key: str, address: str, tx_hash: str, txs: list[dict]) -> bool:
    """Ist `address` die sendende (gas-zahlende) Adresse dieser Transaktion?"""
    if _is_sender(address, txs):
        return True
    if any(t.get("category") == "erc20" for t in txs) and not any(
        t.get("category") in ("external", "internal") for t in txs
    ):
        frm = await _tx_from_via_hash(chain, key, tx_hash)
        return frm == address.lower()
    return False


def _hex_to_int(value) -> int | None:
    if value is None:
        return None
    try:
        return int(str(value), 16)
    except (TypeError, ValueError):
        return None


async def fetch_gas_wei(chain: str, key: str, tx_hash: str) -> int | None:
    """gasUsed * effectiveGasPrice (+ l1Fee auf Base) in Wei — exakt, als int.

    None bei jedem Fehler (Receipt nicht lesbar, Felder fehlen) — der
    Aufrufer setzt dann fee=None + "gebuehr_fehlt", kein Crash.
    """
    try:
        receipt = await ac.call(chain, key, "eth_getTransactionReceipt", [tx_hash])
    except Exception:
        return None
    if not isinstance(receipt, dict):
        return None
    gas_used = _hex_to_int(receipt.get("gasUsed"))
    gas_price = _hex_to_int(receipt.get("effectiveGasPrice"))
    if gas_used is None or gas_price is None:
        return None
    total = gas_used * gas_price
    if chain == "base":
        l1_fee = _hex_to_int(receipt.get("l1Fee"))
        if l1_fee is not None:
            total += l1_fee
    return total


def wei_to_eur(wei: int, day: str | None) -> Decimal | None:
    """Wei -> ETH -> EUR über den ETH-Tageskurs. None ohne Kurs für den Tag."""
    if day is None:
        return None
    series = price_store.get_series("ethereum")
    price = series.get(day)
    if price is None:
        return None
    eth = Decimal(wei) / (Decimal(10) ** 18)
    return eth * Decimal(str(price))


async def sell_side_fee(
    chain: str, key: str, address: str, tx_hash: str, txs: list[dict], day: str | None,
    *, receipts_used: int,
) -> tuple[Decimal | None, bool, int]:
    """Gas-Fee für den sell-Eintrag eines Swaps. Rückgabe (fee_eur, gebuehr_fehlt, receipts_used_neu).

    fee_eur ist None (mit gebuehr_fehlt=True), wenn: Adresse nicht Absender
    (dann ist fee schlicht 0, kein "fehlt" — siehe Aufrufer), Grenze erreicht,
    Receipt-Abruf fehlschlägt, oder kein ETH-Kurs für den Tag vorliegt.
    """
    if receipts_used >= MAX_RECEIPTS_PER_RUN:
        return None, True, receipts_used
    if not await is_sender(chain, key, address, tx_hash, txs):
        return Decimal(0), False, receipts_used
    wei = await fetch_gas_wei(chain, key, tx_hash)
    receipts_used += 1
    if wei is None:
        return None, True, receipts_used
    eur = wei_to_eur(wei, day)
    if eur is None:
        return None, True, receipts_used
    return eur, False, receipts_used
