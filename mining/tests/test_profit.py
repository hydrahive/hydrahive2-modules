"""Ertragsrechnung (reine Funktionen)."""
from __future__ import annotations

import pytest
from backend.profit import CoinQuote, coins_per_hs_day, rank, usd_per_day


def _q(coin="rvn", profit=2.5e-6, price=0.0023, fee_type="PPS+", fee=0.01):
    return CoinQuote(coin=coin, name=coin.upper(), algo="KawPow", fee=fee, fee_type=fee_type,
                     profit_per_hs_day=profit, price_usd=price)


def test_kryptex_value_wins():
    v, est = coins_per_hs_day(kryptex_value=2.5e-6, daily_emission=1.8e6, net_hashrate=6.5e11, fee=0.01)
    assert v == 2.5e-6 and est is False


def test_fallback_from_emission_with_fee():
    v, est = coins_per_hs_day(kryptex_value=None, daily_emission=1000.0, net_hashrate=1e6, fee=0.03)
    assert est is True
    assert v == pytest.approx(1000.0 / 1e6 * 0.97)


@pytest.mark.parametrize("kv,de,nh", [(None, None, 1e6), (None, 1000.0, 0), (0, None, None), (None, 0, 5)])
def test_not_determinable(kv, de, nh):
    assert coins_per_hs_day(kryptex_value=kv, daily_emission=de, net_hashrate=nh, fee=0.01) == (None, False)


def test_usd_per_day_rtx5060ti_rvn():
    # 32 MH/s × 2.57e-6 RVN/(H/s·Tag) × 0.00229 $ ≈ 0.188 $/Tag (Live-Werte 03.10.)
    assert usd_per_day(_q(profit=2.57e-6, price=0.00229), 32e6) == pytest.approx(0.1883, rel=1e-3)


def test_usd_per_day_none_without_price_or_profit():
    assert usd_per_day(_q(price=None), 1e6) is None
    assert usd_per_day(_q(profit=None), 1e6) is None
    assert usd_per_day(_q(), 0) is None


def test_prop_discount_only_for_prop():
    pps = _q(fee_type="PPS+")
    prop = _q(fee_type="PROP")
    assert usd_per_day(pps, 1e6, prop_discount=0.1) == pytest.approx(usd_per_day(pps, 1e6))
    assert usd_per_day(prop, 1e6, prop_discount=0.1) == pytest.approx(usd_per_day(prop, 1e6) * 0.9)


def test_rank_sorted_desc_and_skips_unknown():
    a = _q(coin="a", profit=1e-6, price=1.0)
    b = _q(coin="b", profit=3e-6, price=1.0)
    c = _q(coin="c", profit=9e-6, price=None)      # kein Kurs → raus
    d = _q(coin="d", profit=9e-6, price=1.0)       # keine Hashrate → raus
    rows = rank([a, b, c, d], {"a": 1e6, "b": 1e6, "c": 1e6})
    assert [q.coin for q, _ in rows] == ["b", "a"]
    assert rows[0][1] == pytest.approx(3.0)
