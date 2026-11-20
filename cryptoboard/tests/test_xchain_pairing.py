"""xchain_pairing — reine Paarungsfunktion (kein Netz), Preis aus dem echten Verhältnis."""
from __future__ import annotations


import pytest

from backend import price_history_store as ps
from backend import xchain_pairing as xp

TRON_ADDR = "TUserTronAddress00000000000000000"
EVM_ADDR = "0x" + "a" * 40
SERVICE_ADDR = "0x" + "b" * 40
DAY = "2026-11-17"


def _sell(hash_, ts, amount_sun, fee_sun=1_100_000):
    return {"tron_tx": hash_, "executed_at": ts, "amount_sun": amount_sun, "fee_sun": fee_sun,
            "from": TRON_ADDR, "to": "Tservice00000000000000000000000000"}


def _cand(evm_tx, ts, amount_base_units, decimals, coin_id, symbol, from_=SERVICE_ADDR, chain="base"):
    return {"evm_chain": chain, "evm_tx": evm_tx, "executed_at": ts, "amount_base_units": amount_base_units,
            "decimals": decimals, "coin_id": coin_id, "symbol": symbol, "name": symbol, "from": from_,
            "unresolved": coin_id is None}


@pytest.fixture(autouse=True)
def _prices():
    ps.upsert_series("usd-coin", {DAY: 0.9})
    ps.upsert_series("tron", {DAY: 0.08})
    yield


def test_einfache_paarung_preis_aus_verhaeltnis():
    """8000 TRX raus, 2435.31 USDC rein 60s spaeter, USDC-Kurs 0.9 -> TRX-Preis exakt aus dem Verhältnis."""
    sell = _sell("tx1", f"{DAY}T23:19:00Z", 8_000_000_000, fee_sun=0)
    cand = _cand("0xe1", f"{DAY}T23:20:00Z", 2435310000, 6, "usd-coin", "USDC")
    out = xp.pair_all([sell], [cand], {TRON_ADDR.lower(), EVM_ADDR.lower()})
    assert len(out["pairs"]) == 1
    assert out["mehrdeutig"] == [] and out["unklar_tron"] == []
    pair = out["pairs"][0]
    assert pair["delay_seconds"] == 60
    sell_e, buy_e = pair["entries"]
    assert sell_e["quantity"] == "8000"
    assert buy_e["quantity"] == "2435.31"
    assert buy_e["price"] == "0.9"
    # value_eur = 2435.31 * 0.9 = 2191.779; / 8000 = 0.273972375
    assert sell_e["price"] == "0.273972375"
    assert sell_e["hash"] == "xchain:tx1:base:0xe1:sell"
    assert sell_e["tx_hash"] == "xchain:tx1:base:0xe1"
    assert buy_e["hash"] == "xchain:tx1:base:0xe1:buy"


def test_gebuehr_aus_fee_sun_ueber_tron_kurs():
    sell = _sell("tx1", f"{DAY}T23:19:00Z", 8_000_000_000, fee_sun=1_100_000)  # 1.1 TRX
    cand = _cand("0xe1", f"{DAY}T23:20:00Z", 2435310000, 6, "usd-coin", "USDC")
    out = xp.pair_all([sell], [cand], {TRON_ADDR.lower()})
    sell_e = out["pairs"][0]["entries"][0]
    # 1.1 TRX * 0.08 EUR = 0.088 EUR
    assert sell_e["fee"] == "0.088"
    assert sell_e["gebuehr_fehlt"] is False


def test_gebuehr_fehlt_ohne_fee_sun():
    sell = _sell("tx1", f"{DAY}T23:19:00Z", 8_000_000_000, fee_sun=None)
    cand = _cand("0xe1", f"{DAY}T23:20:00Z", 2435310000, 6, "usd-coin", "USDC")
    out = xp.pair_all([sell], [cand], {TRON_ADDR.lower()})
    sell_e = out["pairs"][0]["entries"][0]
    assert sell_e["fee"] is None
    assert sell_e["gebuehr_fehlt"] is True


def test_kein_kandidat_im_fenster_ist_unklar_nur_raus():
    sell = _sell("tx1", f"{DAY}T23:19:00Z", 8_000_000_000)
    cand = _cand("0xe1", f"{DAY}T23:40:00Z", 2435310000, 6, "usd-coin", "USDC")  # 21 min spaeter
    out = xp.pair_all([sell], [cand], {TRON_ADDR.lower()}, window_minutes=15)
    assert out["pairs"] == []
    assert len(out["unklar_tron"]) == 1
    assert out["unklar_tron"][0]["reason"] == "nur_raus"
    assert out["unklar_tron"][0]["chain"] == "tron"


def test_eingang_vor_dem_abgang_zaehlt_nicht():
    sell = _sell("tx1", f"{DAY}T23:19:00Z", 8_000_000_000)
    cand = _cand("0xe1", f"{DAY}T23:18:00Z", 2435310000, 6, "usd-coin", "USDC")  # VOR dem Abgang
    out = xp.pair_all([sell], [cand], {TRON_ADDR.lower()})
    assert out["pairs"] == []
    assert len(out["unklar_tron"]) == 1


def test_zwei_gleich_nahe_kandidaten_sind_mehrdeutig():
    sell = _sell("tx1", f"{DAY}T23:19:00Z", 8_000_000_000)
    c1 = _cand("0xe1", f"{DAY}T23:20:00Z", 2435310000, 6, "usd-coin", "USDC")
    c2 = _cand("0xe2", f"{DAY}T23:20:00Z", 100000000, 6, "usd-coin", "USDC")  # exakt gleiche Verzoegerung
    out = xp.pair_all([sell], [c1, c2], {TRON_ADDR.lower()})
    assert out["pairs"] == []
    assert len(out["mehrdeutig"]) == 1
    amb = out["mehrdeutig"][0]
    assert amb["tron_tx"] == "tx1"
    assert len(amb["candidates"]) == 2
    assert {c["evm_tx"] for c in amb["candidates"]} == {"0xe1", "0xe2"}


def test_eingang_von_eigener_adresse_wird_nicht_gepaart():
    sell = _sell("tx1", f"{DAY}T23:19:00Z", 8_000_000_000)
    cand = _cand("0xe1", f"{DAY}T23:20:00Z", 2435310000, 6, "usd-coin", "USDC", from_=EVM_ADDR)
    out = xp.pair_all([sell], [cand], {TRON_ADDR.lower(), EVM_ADDR.lower()})
    assert out["pairs"] == []
    assert len(out["unklar_tron"]) == 1


def test_ein_eingang_passt_zu_zwei_abgaengen_nur_einer_bekommt_ihn():
    sell1 = _sell("tx1", f"{DAY}T23:19:00Z", 8_000_000_000)
    sell2 = _sell("tx2", f"{DAY}T23:19:30Z", 4_000_000_000)
    cand = _cand("0xe1", f"{DAY}T23:20:00Z", 2435310000, 6, "usd-coin", "USDC")
    out = xp.pair_all([sell1, sell2], [cand], {TRON_ADDR.lower()})
    # sell1 (frueher, naeher dran: 60s) bekommt den Kandidaten, sell2 bleibt unklar (90s waere noch im Fenster,
    # aber der Kandidat ist bereits verbraucht)
    assert len(out["pairs"]) == 1
    assert out["pairs"][0]["tron_tx"] == "tx1"
    assert len(out["unklar_tron"]) == 1
    assert out["unklar_tron"][0]["hash"] == "tx2"


def test_consumed_evm_eintraege_fuer_dedup_markierung():
    sell = _sell("tx1", f"{DAY}T23:19:00Z", 8_000_000_000)
    cand = _cand("0xe1", f"{DAY}T23:20:00Z", 2435310000, 6, "usd-coin", "USDC")
    out = xp.pair_all([sell], [cand], {TRON_ADDR.lower()})
    assert out["consumed"] == {("base", "0xe1")}


def test_match_candidates_liefert_rohdaten_fuer_weiterverarbeitung():
    sell = _sell("tx1", f"{DAY}T23:19:00Z", 8_000_000_000)
    cand = _cand("0xe1", f"{DAY}T23:20:00Z", 2435310000, 6, "usd-coin", "USDC")
    out = xp.match_candidates([sell], [cand], {TRON_ADDR.lower()})
    assert len(out["matched"]) == 1
    assert out["ambiguous"] == []
    assert out["unmatched"] == []
