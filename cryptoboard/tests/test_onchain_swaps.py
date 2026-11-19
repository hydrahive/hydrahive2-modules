"""onchain_swaps — reine Funktionen, Swap-Regel über Netto-Bewegungen (kein Netz, kein Raten)."""
from __future__ import annotations

from decimal import Decimal

from backend import onchain_swaps as sw

ADDR = "0xAAAA000000000000000000000000000000AAAA"
USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
WETH_BASE = "0x4200000000000000000000000000000000000006"


def _erc20(from_, to, contract, value_hex, decimal_hex, symbol="TOK", hash_="0xh1", ts="2026-01-01T00:00:00Z"):
    return {
        "hash": hash_, "category": "erc20", "from": from_, "to": to,
        "metadata": {"blockTimestamp": ts},
        "rawContract": {"address": contract, "value": value_hex, "decimal": decimal_hex, "symbol": symbol},
    }


def _native(from_, to, value_hex, decimal_hex="0x12", hash_="0xh1", ts="2026-01-01T00:00:00Z"):
    return {
        "hash": hash_, "category": "external", "from": from_, "to": to,
        "metadata": {"blockTimestamp": ts},
        "rawContract": {"address": None, "value": value_hex, "decimal": decimal_hex, "symbol": "ETH"},
    }


def test_eindeutiger_swap_sell_a_buy_b():
    # Adresse sendet USDC raus, bekommt natives ETH rein -> klarer Swap
    txs = [
        _erc20(ADDR.lower(), "0xpool", USDC_BASE, hex(1000 * 10**6), "0x6", symbol="USDC"),
        _native("0xpool", ADDR.lower(), hex(int(0.5 * 1e18)), "0x12"),
    ]
    out = sw.detect_swaps("base", ADDR, txs)
    assert len(out["swaps"]) == 1
    assert out["unklar"] == []
    swap = out["swaps"][0]
    assert swap["sell"]["contract"] == USDC_BASE
    assert swap["sell"]["amount_base_units"] == 1000 * 10**6
    assert swap["buy"]["amount_base_units"] == int(0.5 * 1e18)


def test_nur_raus_ist_unklar():
    txs = [_erc20(ADDR.lower(), "0xpool", USDC_BASE, hex(500 * 10**6), "0x6")]
    out = sw.detect_swaps("base", ADDR, txs)
    assert out["swaps"] == []
    assert len(out["unklar"]) == 1
    assert out["unklar"][0]["reason"] == "mehrdeutige_bewegung"


def test_mehrere_assets_je_seite_ist_unklar():
    txs = [
        _erc20(ADDR.lower(), "0xpool", USDC_BASE, hex(500 * 10**6), "0x6", symbol="USDC"),
        _erc20(ADDR.lower(), "0xpool", "0xother", hex(10 * 10**18), "0x12", symbol="OTH"),
        _native("0xpool", ADDR.lower(), hex(int(0.1 * 1e18)), "0x12"),
    ]
    out = sw.detect_swaps("base", ADDR, txs)
    assert out["swaps"] == []
    assert len(out["unklar"]) == 1


def test_approve_ohne_transfer_ist_unklar():
    """Ein Approve erzeugt keinen Transfer mit Wert > 0 relativ zur Adresse — keine Netto-Bewegung."""
    txs = [_erc20(ADDR.lower(), ADDR.lower(), USDC_BASE, "0x0", "0x6")]
    out = sw.detect_swaps("base", ADDR, txs)
    assert out["swaps"] == []
    assert len(out["unklar"]) == 1
    assert out["unklar"][0]["reason"] == "keine_nettobewegung"


def test_weth_wrap_ist_kein_trade():
    txs = [
        _native(ADDR.lower(), WETH_BASE, hex(int(1 * 1e18)), "0x12"),
        _erc20(WETH_BASE, ADDR.lower(), WETH_BASE, hex(int(1 * 1e18)), "0x12", symbol="WETH"),
    ]
    out = sw.detect_swaps("base", ADDR, txs)
    assert out["swaps"] == []
    assert out["unklar"] == []
    assert len(out["wraps"]) == 1


def test_exaktes_parsing_18_dezimalen_grosser_betrag():
    """Float würde hier runden — amount_base_units muss exakt sein (Integer)."""
    huge_wei = 123456789012345678901  # > 2**64, viele Dezimalstellen
    txs = [
        _erc20(ADDR.lower(), "0xpool", USDC_BASE, hex(1 * 10**6), "0x6", symbol="USDC"),
        _native("0xpool", ADDR.lower(), hex(huge_wei), "0x12"),
    ]
    out = sw.detect_swaps("base", ADDR, txs)
    swap = out["swaps"][0]
    assert swap["buy"]["amount_base_units"] == huge_wei
    # Float-Vergleich zur Kontrolle: float(huge_wei) verliert Präzision, int bleibt exakt
    assert float(huge_wei) != huge_wei or True  # Dokumentation der Eigenschaft, siehe decimal_amount unten
    assert sw.decimal_amount(txs[1]) == Decimal(huge_wei) / Decimal(10**18)


def test_decimal_amount_nutzt_raw_contract_nicht_float_feld():
    t = _erc20(ADDR.lower(), "0xpool", USDC_BASE, hex(998_730_000), "0x6", symbol="USDC")
    assert sw.decimal_amount(t) == Decimal("998.73")


def test_group_by_hash():
    txs = [
        _erc20(ADDR.lower(), "0xpool", USDC_BASE, hex(1), "0x6", hash_="0xa"),
        _native("0xpool", ADDR.lower(), hex(1), "0x12", hash_="0xa"),
        _erc20(ADDR.lower(), "0xpool", USDC_BASE, hex(1), "0x6", hash_="0xb"),
    ]
    grouped = sw.group_by_hash(txs)
    assert set(grouped) == {"0xa", "0xb"}
    assert len(grouped["0xa"]) == 2
    assert len(grouped["0xb"]) == 1
