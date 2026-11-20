"""Read-Port v3 — ledger_moves (VERTRAG-B.md Punkt 3): 2 Swaps gepaart, 1 Kartenzahlung,
1 Abgang, ein verwaistes Bein -> swap_bein_fehlt. Fremder User sieht nichts.
"""
from __future__ import annotations

import pytest

from backend import onchain_import as oi
from backend import portfolio_store as store
from backend import read_port

USER = "testuser"
OTHER = "other"
TRON_TX_1, TRON_TX_2, TRON_TX_3 = "a" * 64, "b" * 64, "c" * 64
EVM_TX_1, EVM_TX_2, EVM_TX_3 = ("0x" + c * 64 for c in "123")
CARD_TX, OUT_TX = "0x" + "d" * 64, "0x" + "e" * 64


def _xchain(tron_tx, evm_tx, kind, **kw):
    defaults = dict(
        user=USER, coin_id="tron" if kind == "sell" else "usd-coin",
        symbol="TRX" if kind == "sell" else "USDC", name="", kind=kind,
        quantity=1000.0 if kind == "sell" else 300.0, price=0.2 if kind == "sell" else 0.9, fee=0.1,
        executed_at="2026-11-01T10:00:00Z", note=oi.NOTE,
        import_hash=f"xchain:{tron_tx}:base:{evm_tx}:{kind}",
    )
    defaults.update(kw)
    return store.add(**defaults)


def _transfer_out(tx_hash, note, **kw):
    defaults = dict(
        user=USER, coin_id="usd-coin", symbol="USDC", name="", kind="transfer_out",
        quantity=100.0, price=0.95, fee=0.0, executed_at="2026-11-05T12:00:00Z", note=note,
        import_hash=f"base:{tx_hash}:transfer_out",
    )
    defaults.update(kw)
    return store.add(**defaults)


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    store.clear_all(USER)
    store.clear_all(OTHER)


def test_zwei_swaps_gepaart_kartenzahlung_abgang_und_verwaistes_bein(client):
    # Swap 1 (vollständig)
    _xchain(TRON_TX_1, EVM_TX_1, "sell", executed_at="2026-11-01T10:00:00Z")
    _xchain(TRON_TX_1, EVM_TX_1, "buy", executed_at="2026-11-01T10:00:05Z")
    # Swap 2 (vollständig, anderer Tag)
    _xchain(TRON_TX_2, EVM_TX_2, "sell", executed_at="2026-11-02T08:00:00Z")
    _xchain(TRON_TX_2, EVM_TX_2, "buy", executed_at="2026-11-02T08:00:05Z")
    # Verwaistes Bein: nur sell, kein passendes buy
    _xchain(TRON_TX_3, EVM_TX_3, "sell", executed_at="2026-11-03T09:00:00Z")
    # Kartenzahlung + Abgang
    _transfer_out(CARD_TX, oi.NOTE_KARTENZAHLUNG, executed_at="2026-11-04T11:00:00Z")
    _transfer_out(OUT_TX, oi.NOTE_ABGANG, executed_at="2026-11-06T13:00:00Z")

    moves = read_port.ledger_moves(USER)
    by_type: dict[str, list[dict]] = {}
    for m in moves:
        by_type.setdefault(m["type"], []).append(m)

    assert len(by_type.get("swap", [])) == 2
    assert len(by_type.get("kartenzahlung", [])) == 1
    assert len(by_type.get("abgang", [])) == 1
    assert len(by_type.get("unklar", [])) == 1
    assert by_type["unklar"][0]["reason"] == "swap_bein_fehlt"

    swap1 = next(m for m in by_type["swap"] if m["id"] == f"xchain:{TRON_TX_1}:base:{EVM_TX_1}")
    assert swap1["from"]["chain"] == "tron" and swap1["from"]["coin_id"] == "tron"
    assert swap1["from"]["quantity"] == "1000.0"
    assert swap1["to"]["chain"] == "base" and swap1["to"]["coin_id"] == "usd-coin"
    assert swap1["to"]["quantity"] == "300.0"
    # value_minor = to.gross_minor = 300 * 0.9 * 100 = 27000 Cent
    assert swap1["value_minor"] == 27000
    assert swap1["from"]["fee_minor"] == 10  # 0.1 EUR -> 10 Cent
    assert swap1["executed_at"] == "2026-11-01T10:00:05Z"  # buy-Zeit laut Vertrag

    kz = by_type["kartenzahlung"][0]
    assert kz["id"] == f"base:{CARD_TX}:transfer_out"
    assert kz["chain"] == "base" and kz["symbol"] == "USDC" and kz["coin_id"] == "usd-coin"
    assert kz["quantity"] == "100.0"
    assert kz["value_minor"] == 9500  # 100 * 0.95 * 100

    ab = by_type["abgang"][0]
    assert ab["id"] == f"base:{OUT_TX}:transfer_out"
    assert ab["value_minor"] == 9500


def test_fremder_user_sieht_nichts(client):
    _xchain(TRON_TX_1, EVM_TX_1, "sell")
    _xchain(TRON_TX_1, EVM_TX_1, "buy")
    _transfer_out(CARD_TX, oi.NOTE_KARTENZAHLUNG)
    assert read_port.ledger_moves(OTHER) == []


def test_csv_import_ohne_onchain_hash_wird_ignoriert(client):
    """Nicht-On-Chain-Einträge (z. B. CSV-Import, kein import_hash) tauchen nicht auf."""
    store.add(USER, coin_id="bitcoin", symbol="BTC", name="", kind="buy", quantity=1.0,
              price=50000.0, fee=0.0, executed_at="2026-01-01T00:00:00Z", note="CSV-Import")
    assert read_port.ledger_moves(USER) == []


def test_since_filtert(client):
    _transfer_out(CARD_TX, oi.NOTE_KARTENZAHLUNG, executed_at="2026-11-01T00:00:00Z")
    _transfer_out(OUT_TX, oi.NOTE_ABGANG, executed_at="2026-11-10T00:00:00Z")
    moves = read_port.ledger_moves(USER, since="2026-11-05T00:00:00Z")
    assert len(moves) == 1
    assert moves[0]["id"] == f"base:{OUT_TX}:transfer_out"


def test_limit_begrenzt():
    for i in range(3):
        _transfer_out(f"0x{i:064d}", oi.NOTE_ABGANG, executed_at=f"2026-11-0{i + 1}T00:00:00Z")
    assert len(read_port.ledger_moves(USER, limit=2)) == 2


def test_quantity_als_decimal_string_value_minor_als_int(client):
    _transfer_out(CARD_TX, oi.NOTE_KARTENZAHLUNG)
    m = read_port.ledger_moves(USER)[0]
    assert isinstance(m["quantity"], str)
    assert isinstance(m["value_minor"], int)
