"""Speicher, Hintergrundjob und Routen."""
from __future__ import annotations

import pytest
from backend import fx, kryptex, poller, store
from backend.profit import CoinQuote

P = "/api/modules/mining"


def _q(coin, profit, price, fee_type="PPS+"):
    return CoinQuote(coin=coin, name=coin.upper(), algo="A", fee=0.01, fee_type=fee_type,
                     profit_per_hs_day=profit, price_usd=price)


@pytest.fixture
def no_net(monkeypatch):
    """Kein echter Abruf: Kryptex + EZB gemockt; Rückgabe steuerbar."""
    state = {"quotes": [_q("rvn", 2.5e-6, 0.002)], "fail": False, "rate": 1.10}

    async def fake_fetch(client=None):
        if state["fail"]:
            raise kryptex.KryptexError("down")
        return state["quotes"]

    async def fake_rate():
        return state["rate"]

    monkeypatch.setattr(kryptex, "fetch_quotes", fake_fetch)
    monkeypatch.setattr(fx, "fetch_usd_per_eur", fake_rate)
    return state


async def test_refresh_stores_and_outage_keeps_last(no_net):
    assert await poller.refresh() == 1
    quotes, fetched = store.load_quotes()
    assert [q.coin for q in quotes] == ["rvn"] and fetched
    no_net["fail"] = True
    assert await poller.refresh() == 0
    quotes2, fetched2 = store.load_quotes()
    assert [q.coin for q in quotes2] == ["rvn"] and fetched2 == fetched


def test_replace_quotes_empty_is_noop():
    store.replace_quotes([_q("rvn", 1e-6, 1.0)])
    store.replace_quotes([])
    assert [q.coin for q in store.load_quotes()[0]] == ["rvn"]


def test_ecb_parse():
    xml = "<Cube currency='JPY' rate='160.1'/><Cube currency='USD' rate='1.1225'/>"
    assert fx.parse_usd_rate(xml) == 1.1225
    assert fx.parse_usd_rate("<Cube currency='USD' rate='99'/>") is None
    assert fx.parse_usd_rate("") is None


def test_overview_requires_login(client):
    assert client.get(f"{P}/overview").status_code == 401


async def test_overview_sorted_with_eur(client, user_headers, no_net):
    no_net["quotes"] = [_q("rvn", 2.5e-6, 0.002), _q("prl", 2e-14, 1.0), _q("iron", 9e-8, None)]
    await poller.refresh()
    r = client.get(f"{P}/overview", headers=user_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["usd_per_eur"] == 1.10
    coins = [row["coin"] for row in body["rows"]]
    assert coins[0] == "prl" and coins[-1] == "iron"   # ohne Kurs ans Ende
    prl = body["rows"][0]
    assert prl["usd_day"] == pytest.approx(2e-14 * 91e12)
    assert prl["eur_day"] == pytest.approx(prl["usd_day"] / 1.10)


def test_overview_unknown_gpu_404(client, user_headers):
    assert client.get(f"{P}/overview?gpu=gibtsnicht", headers=user_headers).status_code == 404


def test_gpus_list(client, user_headers):
    ids = [g["id"] for g in client.get(f"{P}/gpus", headers=user_headers).json()]
    assert "nvidia-rtx-5060-ti-16gb" in ids


def test_config_defaults_and_user_cannot_change(client, user_headers):
    assert client.get(f"{P}/config", headers=user_headers).json()["switch_threshold"] == 0.05
    r = client.put(f"{P}/config", headers=user_headers, json={"region": "us"})
    assert r.status_code == 403


def test_config_admin_change_and_validation(client, admin_headers):
    r = client.put(f"{P}/config", headers=admin_headers, json={"kryptex_user": " till ", "region": "us"})
    assert r.status_code == 200 and r.json()["kryptex_user"] == "till" and r.json()["region"] == "us"
    for bad in ({"region": "mars"}, {"switch_threshold": 2}, {"min_runtime_min": 0},
                {"kryptex_user": "a/b"}, {"switch_threshold": True}, {"min_runtime_min": True},
                {"_usd_per_eur": 5}):
        assert client.put(f"{P}/config", headers=admin_headers, json=bad).status_code == 400, bad
    assert client.get(f"{P}/config", headers=admin_headers).json()["region"] == "us"


def test_config_all_or_nothing(client, admin_headers):
    r = client.put(f"{P}/config", headers=admin_headers, json={"region": "sg", "switch_threshold": 9})
    assert r.status_code == 400
    assert client.get(f"{P}/config", headers=admin_headers).json()["region"] != "sg"


def test_refresh_requires_control(client, user_headers, admin_headers, no_net):
    assert client.post(f"{P}/refresh", headers=user_headers).status_code == 403
    r = client.post(f"{P}/refresh", headers=admin_headers)
    assert r.status_code == 200 and r.json() == {"coins": 1}
