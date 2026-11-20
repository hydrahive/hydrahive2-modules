"""preview_all-Route — ganzer Weg gemockt: Base-Swap, Tron-Abgang <-> Base-Eingang (Paar),
Spam-Eingang, reine Ausgabe, eine kaputte Adresse bricht die übrigen NICHT ab.
"""
from __future__ import annotations

import pytest

from backend import addresses_store, alchemy_client as ac, alchemy_key, client as cg
from backend import onchain_resolve as rs, portfolio_store, price_history, price_history_store as ps
from backend import tron_history as th

PREFIX = "/api/modules/cryptoboard"
URL_ALL = f"{PREFIX}/portfolio/import/onchain/preview_all"
USER = "testuser"
KEY = "GEHEIMKEY-preview-all-1234567890"
ADDR_BASE = "0x" + "a" * 40
ADDR_BASE_2 = "0x" + "e" * 40  # zweite Base-Adresse: liefert den Alchemy-Fehler
ADDR_TRON = "TUserTronAddress00000000000000000"
POOL = "0xpool00000000000000000000000000000000000"
SERVICE = "0x" + "b" * 40  # fremder Dienst-Absender auf Base, Ziel des TRX-Pairings
USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
DAY = "2026-11-18"
TS = f"{DAY}T12:00:00.000Z"
H_SWAP, H_PAIR, H_SPAM, H_OUT, H_SPAM_OUT = (("0x" + c * 64) for c in "12345")
FAKE_USDC_CONTRACT = "0x" + "9" * 40  # fremder Kontrakt, NICHT die echte USDC-Adresse


def _erc20(h, frm, to, contract, value, dec, sym):
    return {"hash": h, "blockNum": "0x10", "category": "erc20", "from": frm, "to": to, "asset": sym,
            "metadata": {"blockTimestamp": TS},
            "rawContract": {"address": contract, "value": hex(value), "decimal": hex(dec), "symbol": sym}}


def _eth(h, frm, to, value, category="external"):
    return {"hash": h, "blockNum": "0x10", "category": category, "from": frm, "to": to, "asset": "ETH",
            "metadata": {"blockTimestamp": TS},
            "rawContract": {"address": None, "value": hex(value), "decimal": "0x12"}}


# Adresse 1 (ADDR_BASE): ein Swap (USDC -> ETH), ein Spam-Eingang, eine reine Ausgabe, ein Pairing-Eingang.
TRANSFERS_BASE_1 = [
    _erc20(H_SWAP, ADDR_BASE, POOL, USDC, 1000 * 10**6, 6, "USDC"),
    _eth(H_SWAP, POOL, ADDR_BASE, 5 * 10**17, "internal"),
    _erc20(H_SPAM, "0xdrop00000000000000000000000000000000000", ADDR_BASE, "0x" + "9" * 40,
           1_000_000 * 10**18, 18, "ꓴ឵ՏᎠ"),
    _eth(H_OUT, ADDR_BASE, "0xsink0000000000000000000000000000000000", 2 * 10**17),
    _erc20(H_PAIR, SERVICE, ADDR_BASE, USDC, 2435310000, 6, "USDC"),
    # Fake-"USDC" (fremder Kontrakt) RAUS -> muss Spam sein, nie Ausgabe (Till 20.11.2026).
    _erc20(H_SPAM_OUT, ADDR_BASE, "0xecca0000000000000000000000000000000000", FAKE_USDC_CONTRACT,
           500 * 10**18, 18, "USDC"),
]


@pytest.fixture
def setup(client, monkeypatch):
    rs.clear_contract_cache()
    fetch_calls: list[dict] = []

    async def fake_fetch(chain, key, address, *, to_block="latest", **kw):
        fetch_calls.append({"chain": chain, "address": address})
        if address == ADDR_BASE:
            return {"transfers": TRANSFERS_BASE_1, "truncated": False, "before_block": None}
        if address == ADDR_BASE_2:
            raise ac.AlchemyHttpError(500, "boom")
        return {"transfers": [], "truncated": False, "before_block": None}

    async def fake_call(chain, key, method, params):
        if method == "eth_getTransactionReceipt":
            return {"gasUsed": hex(100000), "effectiveGasPrice": hex(10**9), "l1Fee": hex(0)}
        if method == "eth_getTransactionByHash":
            # from: für onchain_gas.is_sender (Gas-Zahler). to: für onchain_card_detect
            # (Kartenzahlungs-Erkennung) -- je Tx-Hash passend zum jeweiligen Test-Transfer.
            to_by_hash = {H_OUT.lower(): "0xsink0000000000000000000000000000000000"}
            return {"from": ADDR_BASE, "to": to_by_hash.get(str(params[0]).lower())}
        raise AssertionError(method)

    async def fake_contract(platform, address):
        return None

    async def no_fetch(ids, **kw):
        return {}

    async def fake_tron_fetch(address, **kw):
        if address != ADDR_TRON:
            return {"transfers": [], "truncated": False, "before_timestamp": None}
        return {"transfers": [{
            "hash": "trontx1", "executed_at": f"{DAY}T11:59:00Z", "timestamp_ms": 0,
            "from": ADDR_TRON, "to": SERVICE, "amount_sun": 8_000_000_000, "fee_sun": 1_100_000,
        }], "truncated": False, "before_timestamp": None}

    monkeypatch.setattr(ac, "fetch_transfers", fake_fetch)
    monkeypatch.setattr(ac, "call", fake_call)
    monkeypatch.setattr(cg, "contract", fake_contract)
    monkeypatch.setattr(price_history, "ensure_coins", no_fetch)
    monkeypatch.setattr(th, "fetch_transfers", fake_tron_fetch)
    monkeypatch.setattr(alchemy_key, "get_key", lambda user: KEY)
    ps.upsert_series("usd-coin", {DAY: 0.9})
    ps.upsert_series("ethereum", {DAY: 2000.0})
    ps.upsert_series("tron", {DAY: 0.08})

    ids = [
        addresses_store.add(USER, "base", ADDR_BASE, "Base-Haupt"),
        addresses_store.add(USER, "base", ADDR_BASE_2, "Base-Kaputt"),
        addresses_store.add(USER, "tron", ADDR_TRON, "Tron"),
    ]
    yield {"ids": ids, "fetch_calls": fetch_calls}
    portfolio_store.clear_all(USER)
    for i in ids:
        addresses_store.remove(USER, i)
    rs.clear_contract_cache()


def _preview_all(client, auth_headers, **body):
    r = client.post(URL_ALL, json=body, headers=auth_headers)
    assert r.status_code == 200, r.text
    return r.json()


def test_adressen_status_eine_kaputte_bricht_nicht_ab(client, auth_headers, setup):
    data = _preview_all(client, auth_headers)
    by_addr = {a["address"]: a for a in data["addresses"]}
    assert by_addr[ADDR_BASE]["status"] == "ok"
    assert by_addr[ADDR_BASE_2]["status"] == "fehler"
    assert by_addr[ADDR_BASE_2]["error"] == "alchemy_fetch_failed"
    assert by_addr[ADDR_TRON]["status"] == "ok"


def test_swap_auf_erster_adresse_erkannt(client, auth_headers, setup):
    data = _preview_all(client, auth_headers)
    tx = {t["hash"]: t for t in data["transactions"]}
    sell = tx[f"base:{H_SWAP}:sell"]
    buy = tx[f"base:{H_SWAP}:buy"]
    assert (sell["coin_id"], sell["quantity"], sell["price"]) == ("usd-coin", "1000", "0.9")
    assert (buy["coin_id"], buy["quantity"], buy["price"]) == ("ethereum", "0.5", "1800")


def test_spam_eingang_landet_in_spam_nicht_in_unklar_oder_transactions(client, auth_headers, setup):
    data = _preview_all(client, auth_headers)
    assert len(data["spam"]) == 2  # Spam-Eingang (dieser Test) + Spam-Abgang (eigener Test)
    spam = next(s for s in data["spam"] if s["hash"] == H_SPAM.lower())
    assert spam["grund"] == "symbol_nicht_ascii"
    assert all(t["hash"] != f"base:{H_SPAM}:buy" for t in data["transactions"])
    assert all(str(u.get("hash")).lower() != H_SPAM.lower() for u in data["unklar"])


def test_spam_abgang_landet_in_spam_nie_in_ausgaben(client, auth_headers, setup):
    """Fake-"USDC" (fremder Kontrakt) als Abgang -> spam, NIE ausgaben (Till 20.11.2026)."""
    data = _preview_all(client, auth_headers)
    spam_hashes = {s["hash"] for s in data["spam"]}
    assert H_SPAM_OUT.lower() in spam_hashes
    spam_out = next(s for s in data["spam"] if s["hash"] == H_SPAM_OUT.lower())
    assert spam_out["grund"] == "unbekannter_token"
    assert spam_out["contract"] == FAKE_USDC_CONTRACT
    assert all(a["hash"] != f"base:{H_SPAM_OUT}:transfer_out" for a in data["ausgaben"])


def test_echtes_usdc_bleibt_ausgabe_gegenprobe(client, auth_headers, setup):
    """Gegenprobe zum Spam-Abgang: ECHTES USDC (bekannter Kontrakt) bleibt ganz normal Ausgabe."""
    data = _preview_all(client, auth_headers)
    out_hashes = {a["hash"] for a in data["ausgaben"]}
    assert f"base:{H_OUT}:transfer_out" in out_hashes
    assert all(s["hash"] != H_OUT.lower() for s in data["spam"])


def test_reine_ausgabe_wird_transfer_out(client, auth_headers, setup):
    data = _preview_all(client, auth_headers)
    assert len(data["ausgaben"]) == 1
    out = data["ausgaben"][0]
    assert out["hash"] == f"base:{H_OUT}:transfer_out"
    assert out["kind"] == "transfer_out"
    assert out["coin_id"] == "ethereum"
    assert out["price"] == "2000"
    assert out["quantity"] == "0.2"


def test_ausgabe_ohne_konfigurierten_card_kontrakt_ist_abgang(client, auth_headers, setup, monkeypatch):
    """Chain ohne Eintrag in METAMASK_CARD_CONTRACTS -> jede Ausgabe ist "abgang" (kein falscher Treffer)."""
    from backend import onchain_card_detect as card

    monkeypatch.delitem(card.METAMASK_CARD_CONTRACTS, "base", raising=False)
    card.clear_cache()
    data = _preview_all(client, auth_headers)
    out = data["ausgaben"][0]
    assert out["art"] == "abgang"
    assert out["art_unklar"] is False


def test_ausgabe_mit_konfiguriertem_card_kontrakt_wird_kartenzahlung(client, auth_headers, setup, monkeypatch):
    """Mit konfiguriertem Card-Kontrakt (Ziel der Ausgabe = Card) -> art kartenzahlung."""
    from backend import onchain_card_detect as card

    card_contract = "0xsink0000000000000000000000000000000000"  # Ziel von H_OUT (siehe TRANSFERS_BASE_1)
    monkeypatch.setitem(card.METAMASK_CARD_CONTRACTS, "base", card_contract)
    card.clear_cache()
    data = _preview_all(client, auth_headers)
    out = next(a for a in data["ausgaben"] if a["hash"] == f"base:{H_OUT}:transfer_out")
    assert out["art"] == "kartenzahlung"
    assert out["art_unklar"] is False
    card.clear_cache()


def test_tron_base_paar_erkannt_mit_preis_und_gebuehr(client, auth_headers, setup):
    data = _preview_all(client, auth_headers)
    assert len(data["pairs"]) == 1
    pair = data["pairs"][0]
    assert pair["tron_tx"] == "trontx1"
    assert pair["evm_chain"] == "base"
    assert pair["evm_tx"] == H_PAIR.lower()
    sell_e, buy_e = pair["entries"]
    assert sell_e["kind"] == "sell" and sell_e["coin_id"] == "tron" and sell_e["quantity"] == "8000"
    assert buy_e["kind"] == "buy" and buy_e["coin_id"] == "usd-coin" and buy_e["quantity"] == "2435.31"
    assert sell_e["fee"] == "0.088" and sell_e["gebuehr_fehlt"] is False
    assert pair["id"] == f"xchain:trontx1:base:{H_PAIR.lower()}"


def test_gepaarter_eingang_nicht_zusaetzlich_in_unklar(client, auth_headers, setup):
    data = _preview_all(client, auth_headers)
    assert all(u.get("hash") != H_PAIR.lower() for u in data["unklar"])


def test_counts_und_buchbar(client, auth_headers, setup):
    data = _preview_all(client, auth_headers)
    c = data["counts"]
    assert c["swaps"] == 1
    assert c["pairs"] == 1
    assert c["spam"] == 2  # ein Spam-Eingang + ein Spam-Abgang
    assert c["ausgaben"] == 1
    assert c["mehrdeutig"] == 0
    assert c["buchbar"] > 0


def test_window_minutes_wird_durchgereicht(client, auth_headers, setup):
    data = _preview_all(client, auth_headers, window_minutes=5)
    assert data["window_minutes"] == 5
    assert len(data["pairs"]) == 1


def test_ohne_alchemy_key_schlaegt_komplett_fehl(client, auth_headers, setup, monkeypatch):
    monkeypatch.setattr(alchemy_key, "get_key", lambda user: None)
    r = client.post(URL_ALL, json={}, headers=auth_headers)
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "alchemy_key_missing"


def test_kill_switch_aus_schlaegt_komplett_fehl(client, auth_headers, setup, monkeypatch):
    monkeypatch.setattr(ac, "enabled", lambda: False)
    r = client.post(URL_ALL, json={}, headers=auth_headers)
    assert r.status_code == 503
    assert r.json()["detail"]["code"] == "cryptoboard_onchain_disabled"


def test_duplicate_wird_markiert(client, auth_headers, setup):
    first = _preview_all(client, auth_headers)
    swap_sell = next(t for t in first["transactions"] if t["hash"] == f"base:{H_SWAP}:sell")
    portfolio_store.add(
        USER, coin_id=swap_sell["coin_id"], symbol=swap_sell["symbol"], name="", kind="sell",
        quantity=float(swap_sell["quantity"]), price=float(swap_sell["price"]), fee=0.0,
        executed_at=swap_sell["executed_at"], note="t", import_hash=swap_sell["hash"],
    )
    second = _preview_all(client, auth_headers)
    sell2 = next(t for t in second["transactions"] if t["hash"] == f"base:{H_SWAP}:sell")
    assert sell2["duplicate"] is True
