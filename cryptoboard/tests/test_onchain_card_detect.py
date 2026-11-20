"""onchain_card_detect — Kartenzahlung-Erkennung (VERTRAG-B.md Punkt 2): Tx-to == Card-Kontrakt,
Cache je (chain, tx_hash), Obergrenze MAX_LOOKUPS_PER_RUN, kein Raten bei Fehlern/Grenze.
"""
from __future__ import annotations

import pytest

from backend import alchemy_client as ac
from backend import onchain_card_detect as card

CHAIN = "base"
KEY = "testkey"
CARD_CONTRACT = "0x" + "d" * 40
OTHER_CONTRACT = "0x" + "e" * 40
TX_CARD = "0x" + "1" * 64
TX_OTHER = "0x" + "2" * 64


@pytest.fixture(autouse=True)
def _reset():
    card.clear_cache()
    yield
    card.clear_cache()


@pytest.fixture
def with_card_contract(monkeypatch):
    monkeypatch.setitem(card.METAMASK_CARD_CONTRACTS, CHAIN, CARD_CONTRACT)
    yield
    card.METAMASK_CARD_CONTRACTS.pop(CHAIN, None)


async def test_treffer_ist_kartenzahlung(monkeypatch, with_card_contract):
    async def fake_call(chain, key, method, params):
        assert method == "eth_getTransactionByHash"
        return {"to": CARD_CONTRACT.upper()}  # Groß/klein darf keine Rolle spielen

    monkeypatch.setattr(ac, "call", fake_call)
    art, art_unklar, used = await card.classify_art(CHAIN, KEY, TX_CARD, lookups_used=0)
    assert art == "kartenzahlung" and art_unklar is False and used == 1


async def test_anderes_ziel_ist_abgang(monkeypatch, with_card_contract):
    async def fake_call(chain, key, method, params):
        return {"to": OTHER_CONTRACT}

    monkeypatch.setattr(ac, "call", fake_call)
    art, art_unklar, used = await card.classify_art(CHAIN, KEY, TX_OTHER, lookups_used=0)
    assert art == "abgang" and art_unklar is False


async def test_ohne_konfigurierten_kontrakt_kein_lookup_abgang(monkeypatch):
    """Chain ohne Eintrag in METAMASK_CARD_CONTRACTS -> kein Netzaufruf, immer "abgang"."""
    calls = []

    async def fake_call(chain, key, method, params):
        calls.append(1)
        return {"to": OTHER_CONTRACT}

    monkeypatch.setattr(ac, "call", fake_call)
    art, art_unklar, used = await card.classify_art(CHAIN, KEY, TX_OTHER, lookups_used=0)
    assert art == "abgang" and art_unklar is False
    assert calls == []
    assert used == 0


async def test_fehlerhafter_abruf_ist_abgang_mit_art_unklar(monkeypatch, with_card_contract):
    async def fake_call(chain, key, method, params):
        raise RuntimeError("boom")

    monkeypatch.setattr(ac, "call", fake_call)
    art, art_unklar, used = await card.classify_art(CHAIN, KEY, TX_CARD, lookups_used=0)
    assert art == "abgang" and art_unklar is True
    assert used == 1


async def test_grenze_erreicht_kein_lookup_art_unklar(monkeypatch, with_card_contract):
    calls = []

    async def fake_call(chain, key, method, params):
        calls.append(1)
        return {"to": CARD_CONTRACT}

    monkeypatch.setattr(ac, "call", fake_call)
    art, art_unklar, used = await card.classify_art(
        CHAIN, KEY, TX_CARD, lookups_used=card.MAX_LOOKUPS_PER_RUN)
    assert art == "abgang" and art_unklar is True
    assert calls == []  # Grenze erreicht -> kein zusätzlicher Netzaufruf
    assert used == card.MAX_LOOKUPS_PER_RUN


async def test_cache_verhindert_zweiten_netzabruf(monkeypatch, with_card_contract):
    """Der Prozess-Cache (Schlüssel chain+tx_hash) verhindert den zweiten ECHTEN Netzaufruf,
    auch wenn classify_art selbst ein zweites Mal für denselben Hash aufgerufen wird (z. B. ein
    zweiter preview_all-Lauf). lookups_used steigt bei jedem NICHT durch die Grenze abgewiesenen
    Aufruf (auch Cache-Hits zählen als "ein Lookup-Versuch dieses Laufs") — nur der teure
    eth_getTransactionByHash-Call selbst wird eingespart."""
    calls = []

    async def fake_call(chain, key, method, params):
        calls.append(1)
        return {"to": CARD_CONTRACT}

    monkeypatch.setattr(ac, "call", fake_call)
    art1, _, used1 = await card.classify_art(CHAIN, KEY, TX_CARD, lookups_used=0)
    art2, _, used2 = await card.classify_art(CHAIN, KEY, TX_CARD, lookups_used=used1)
    assert art1 == art2 == "kartenzahlung"
    assert len(calls) == 1  # zweiter Aufruf kam aus dem Cache, kein zweiter Netz-Call
    assert used1 == 1 and used2 == 2  # Zähler steigt trotzdem je Aufruf (Grenze bleibt wirksam)
