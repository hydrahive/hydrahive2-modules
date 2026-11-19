"""onchain_gas — Gas-Fee nur als Absender, l1Fee auf Base, Grenze N, Kurs-Fallback."""
from __future__ import annotations

from decimal import Decimal

import pytest

from backend import alchemy_client as ac
from backend import onchain_gas as gas
from backend import price_history_store as price_store


def _tx(category, from_, to_, hash_="0xh1"):
    return {"hash": hash_, "category": category, "from": from_, "to": to_}


# ---------------------------------------------------------------- is_sender


@pytest.mark.asyncio
async def test_is_sender_true_wenn_adresse_from_eines_externen_transfers():
    txs = [_tx("external", "0xaa", "0xpool")]
    assert await gas.is_sender("base", "k", "0xaa", "0xh1", txs) is True


@pytest.mark.asyncio
async def test_is_sender_false_wenn_adresse_empfaenger():
    txs = [_tx("external", "0xpool", "0xaa")]
    assert await gas.is_sender("base", "k", "0xaa", "0xh1", txs) is False


@pytest.mark.asyncio
async def test_is_sender_fallback_ueber_tx_hash_bei_nur_erc20(monkeypatch):
    async def fake_call(chain, key, method, params):
        assert method == "eth_getTransactionByHash"
        return {"from": "0xaa"}
    monkeypatch.setattr(ac, "call", fake_call)
    txs = [_tx("erc20", "0xaa", "0xpool")]  # erc20 "from" ist Token-from, nicht zwingend Tx-from
    assert await gas.is_sender("base", "k", "0xaa", "0xh1", txs) is True


@pytest.mark.asyncio
async def test_is_sender_fallback_liefert_false_bei_anderem_absender(monkeypatch):
    async def fake_call(chain, key, method, params):
        return {"from": "0xandererabsender"}
    monkeypatch.setattr(ac, "call", fake_call)
    txs = [_tx("erc20", "0xaa", "0xpool")]
    assert await gas.is_sender("base", "k", "0xaa", "0xh1", txs) is False


# ---------------------------------------------------------------- fetch_gas_wei / l1Fee


@pytest.mark.asyncio
async def test_fetch_gas_wei_ethereum_ohne_l1fee(monkeypatch):
    async def fake_call(chain, key, method, params):
        return {"gasUsed": hex(21000), "effectiveGasPrice": hex(20_000_000_000)}
    monkeypatch.setattr(ac, "call", fake_call)
    wei = await gas.fetch_gas_wei("ethereum", "k", "0xh1")
    assert wei == 21000 * 20_000_000_000


@pytest.mark.asyncio
async def test_fetch_gas_wei_base_addiert_l1fee(monkeypatch):
    async def fake_call(chain, key, method, params):
        return {"gasUsed": hex(21000), "effectiveGasPrice": hex(1_000_000), "l1Fee": hex(500_000_000)}
    monkeypatch.setattr(ac, "call", fake_call)
    wei = await gas.fetch_gas_wei("base", "k", "0xh1")
    assert wei == 21000 * 1_000_000 + 500_000_000


@pytest.mark.asyncio
async def test_fetch_gas_wei_fehler_liefert_none(monkeypatch):
    async def boom(chain, key, method, params):
        raise RuntimeError("netz kaputt")
    monkeypatch.setattr(ac, "call", boom)
    assert await gas.fetch_gas_wei("base", "k", "0xh1") is None


@pytest.mark.asyncio
async def test_fetch_gas_wei_fehlende_felder_liefert_none(monkeypatch):
    async def fake_call(chain, key, method, params):
        return {"gasUsed": hex(21000)}  # effectiveGasPrice fehlt
    monkeypatch.setattr(ac, "call", fake_call)
    assert await gas.fetch_gas_wei("base", "k", "0xh1") is None


# ---------------------------------------------------------------- wei_to_eur


def test_wei_to_eur_mit_kurs():
    price_store.upsert_series("ethereum", {"2026-06-15": 3000.0})
    eur = gas.wei_to_eur(10**18, "2026-06-15")  # 1 ETH
    assert eur == Decimal("3000")


def test_wei_to_eur_ohne_kurs_none():
    assert gas.wei_to_eur(10**18, "2026-06-16") is None


def test_wei_to_eur_ohne_tag_none():
    assert gas.wei_to_eur(10**18, None) is None


# ---------------------------------------------------------------- sell_side_fee (Zusammenspiel)


@pytest.mark.asyncio
async def test_sell_side_fee_nicht_absender_ist_null_gebuehr_ohne_flag(monkeypatch):
    txs = [_tx("external", "0xpool", "0xaa")]  # Adresse ist Empfänger, nicht Absender

    async def boom(*a, **kw):
        raise AssertionError("kein Receipt-Call nötig, wenn nicht Absender")
    monkeypatch.setattr(ac, "call", boom)
    fee, missing, used = await gas.sell_side_fee("base", "k", "0xaa", "0xh1", txs, "2026-06-15", receipts_used=0)
    assert fee == Decimal(0)
    assert missing is False
    assert used == 0


@pytest.mark.asyncio
async def test_sell_side_fee_absender_mit_kurs(monkeypatch):
    txs = [_tx("external", "0xaa", "0xpool")]
    price_store.upsert_series("ethereum", {"2026-06-15": 2000.0})

    async def fake_call(chain, key, method, params):
        return {"gasUsed": hex(100_000), "effectiveGasPrice": hex(10**9)}  # 0.0001 ETH
    monkeypatch.setattr(ac, "call", fake_call)
    fee, missing, used = await gas.sell_side_fee("base", "k", "0xaa", "0xh1", txs, "2026-06-15", receipts_used=0)
    assert missing is False
    assert fee == Decimal("0.2")  # 0.0001 ETH * 2000 EUR
    assert used == 1


@pytest.mark.asyncio
async def test_sell_side_fee_grenze_erreicht_gebuehr_fehlt(monkeypatch):
    txs = [_tx("external", "0xaa", "0xpool")]

    async def boom(*a, **kw):
        raise AssertionError("Grenze erreicht -> kein weiterer Receipt-Call")
    monkeypatch.setattr(ac, "call", boom)
    fee, missing, used = await gas.sell_side_fee(
        "base", "k", "0xaa", "0xh1", txs, "2026-06-15", receipts_used=gas.MAX_RECEIPTS_PER_RUN,
    )
    assert fee is None
    assert missing is True
    assert used == gas.MAX_RECEIPTS_PER_RUN


@pytest.mark.asyncio
async def test_sell_side_fee_kein_kurs_gebuehr_fehlt(monkeypatch):
    txs = [_tx("external", "0xaa", "0xpool")]

    async def fake_call(chain, key, method, params):
        return {"gasUsed": hex(100_000), "effectiveGasPrice": hex(10**9)}
    monkeypatch.setattr(ac, "call", fake_call)
    fee, missing, used = await gas.sell_side_fee("base", "k", "0xaa", "0xh1", txs, "2099-01-01", receipts_used=0)
    assert fee is None
    assert missing is True
    assert used == 1
