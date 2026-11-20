"""onchain_import.commit_entries — erweiterte Hash-Formate (xchain, transfer_out), direkt (kein Netz)."""
from __future__ import annotations

from decimal import Decimal

import pytest

from backend import onchain_import as oi
from backend import portfolio_store as store
from backend.onchain_import_routes import OnchainCommitTx

USER = "testuser"
TRON_TX = "a" * 64
EVM_TX = "0x" + "b" * 64
BASE_TX = "0x" + "c" * 64


def _tx(**kw):
    defaults = dict(coin_id="tron", symbol="TRX", name="", kind="sell",
                     quantity=Decimal("8000"), price=Decimal("0.27"), fee=Decimal("0.1"),
                     executed_at="2026-11-17T23:19:00Z", hash=f"xchain:{TRON_TX}:base:{EVM_TX}:sell")
    defaults.update(kw)
    return OnchainCommitTx(**defaults)


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    store.clear_all(USER)


def test_xchain_hash_wird_angenommen():
    r = oi.commit_entries(USER, [_tx()])
    assert r["imported"] == 1 and r["skipped"] == 0
    rows = store.list_for(USER)
    assert rows[0]["import_hash"] == f"xchain:{TRON_TX}:base:{EVM_TX}:sell"
    assert rows[0]["kind"] == "sell"


def test_xchain_buy_hash_wird_angenommen():
    t = _tx(kind="buy", coin_id="usd-coin", symbol="USDC", quantity=Decimal("2435.31"),
             price=Decimal("0.9"), fee=None, hash=f"xchain:{TRON_TX}:base:{EVM_TX}:buy")
    r = oi.commit_entries(USER, [t])
    assert r["imported"] == 1


def test_xchain_hash_dedup_bei_zweitem_commit():
    t = _tx()
    r1 = oi.commit_entries(USER, [t])
    assert r1["imported"] == 1
    r2 = oi.commit_entries(USER, [t])
    assert r2["imported"] == 0 and r2["skipped"] == 1
    assert r2["skipped_details"][0]["reason"] == "duplikat"
    assert len(store.list_for(USER)) == 1


def test_transfer_out_hash_format():
    t = _tx(kind="transfer_out", coin_id="usd-coin", symbol="USDC", price=None, fee=None,
             hash=f"base:{BASE_TX}:transfer_out")
    r = oi.commit_entries(USER, [t])
    assert r["imported"] == 1
    row = store.list_for(USER)[0]
    assert row["kind"] == "transfer_out"
    assert row["price"] == 0.0
    assert row["fee"] == 0.0


def test_transfer_out_ohne_preis_wird_nicht_abgelehnt():
    """VERTRAG.md: transfer_out ohne price -> als 0 gebucht, kein Blocker."""
    t = _tx(kind="transfer_out", coin_id="usd-coin", price=None, fee=None,
             hash=f"base:{BASE_TX}:transfer_out")
    r = oi.commit_entries(USER, [t])
    assert r["imported"] == 1 and r["skipped"] == 0


def test_buy_sell_ohne_preis_bleibt_abgelehnt():
    """Der alte Weg (buy/sell ohne price -> preis_fehlt) bleibt unveraendert."""
    t = _tx(kind="sell", price=None)
    r = oi.commit_entries(USER, [t])
    assert r["imported"] == 0
    assert r["skipped_details"][0]["reason"] == "preis_fehlt"


def test_falsches_kind_suffix_am_xchain_hash_abgelehnt():
    t = _tx(kind="buy", hash=f"xchain:{TRON_TX}:base:{EVM_TX}:sell")  # hash sagt sell, kind ist buy
    r = oi.commit_entries(USER, [t])
    assert r["imported"] == 0
    assert r["skipped_details"][0]["reason"] == "hash_ungueltig"


def test_xchain_hash_mit_ethereum_chain():
    t = _tx(hash=f"xchain:{TRON_TX}:ethereum:{EVM_TX}:sell")
    r = oi.commit_entries(USER, [t])
    assert r["imported"] == 1


def test_alter_hash_weg_unveraendert():
    t = _tx(kind="sell", hash=f"base:{BASE_TX}:sell")
    r = oi.commit_entries(USER, [t])
    assert r["imported"] == 1
