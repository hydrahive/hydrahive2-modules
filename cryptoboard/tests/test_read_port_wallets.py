"""Read-Port v2 — Wallet-Erweiterung (wallet_addresses_for, wallet_holdings), VERTRAG-PORT-V2.md.

Prüft: eigene Adressen sichtbar, fremde address_id -> WalletAddressNotFound,
Gesamtwert identisch zu wallets.balances für dieselben Adressen, complete=False
bei fehlendem Kurs, Netzfehler -> PortfolioUnavailable, PORT_VERSION == 3 (v2-Verhalten unveraendert).

Netz (chain_clients.fetch_balance, CoinGecko-Kurse) gemockt wie in test_wallets.py.
"""
from __future__ import annotations

import pytest

from backend import addresses_store, chain_clients, client as cg
from backend import read_port
from backend import wallets


@pytest.fixture
def two_addresses(client):
    """Zwei eigene Adressen (tron + base) von "testuser", eine fremde Adresse von "other"."""
    tron_id = addresses_store.add("testuser", "tron", "T" + "9" * 33, "Haupt-Tron")
    base_id = addresses_store.add("testuser", "base", "0x" + "a" * 40, "Haupt-Base")
    other_id = addresses_store.add("other", "tron", "T" + "8" * 33, "Fremd")
    yield {"tron_id": tron_id, "base_id": base_id, "other_id": other_id}
    addresses_store.remove("testuser", tron_id)
    addresses_store.remove("testuser", base_id)
    addresses_store.remove("other", other_id)


def _mock_balances(monkeypatch):
    async def fake_fetch(chain, address):
        return {
            "tron": [{"symbol": "TRX", "amount": 1000.0, "coin_id": "tron"}],
            "base": [{"symbol": "USDC", "amount": 500.0, "coin_id": "usd-coin"}],
        }.get(chain, [])

    async def fake_markets(vs, *, ids=None, top=None):
        p = {"tron": 0.20, "usd-coin": 0.90}
        return [{"id": i, "price": p.get(i, 0)} for i in (ids or [])]

    monkeypatch.setattr(chain_clients, "fetch_balance", fake_fetch)
    monkeypatch.setattr(cg, "markets", fake_markets)


# ---------------------------------------------------------------- wallet_addresses_for
def test_wallet_addresses_for_nur_eigene(client, two_addresses):
    out = read_port.wallet_addresses_for("testuser")
    ids = {a["id"] for a in out}
    assert ids == {two_addresses["tron_id"], two_addresses["base_id"]}
    assert two_addresses["other_id"] not in ids


def test_wallet_addresses_for_form(client, two_addresses):
    out = read_port.wallet_addresses_for("testuser")
    by_id = {a["id"]: a for a in out}
    tron = by_id[two_addresses["tron_id"]]
    assert tron["chain"] == "tron" and tron["label"] == "Haupt-Tron"
    assert set(tron.keys()) == {"id", "chain", "address", "label"}


def test_wallet_addresses_for_leer_ohne_adressen(client):
    assert read_port.wallet_addresses_for("ohne-wallets") == []


# ---------------------------------------------------------------- wallet_holdings
async def test_wallet_holdings_fremde_id_wirft(client, two_addresses, monkeypatch):
    _mock_balances(monkeypatch)
    with pytest.raises(read_port.WalletAddressNotFound):
        await read_port.wallet_holdings("testuser", [two_addresses["other_id"]])


async def test_wallet_holdings_unbekannte_id_wirft(client, two_addresses, monkeypatch):
    _mock_balances(monkeypatch)
    with pytest.raises(read_port.WalletAddressNotFound):
        await read_port.wallet_holdings("testuser", [999999])


async def test_wallet_holdings_wert_identisch_zu_wallets_balances(client, two_addresses, monkeypatch):
    """Vertrag: Gesamtwert MUSS dem Cryptoboard (Wallets-Ansicht) für dieselben Adressen entsprechen."""
    _mock_balances(monkeypatch)
    addr_ids = [two_addresses["tron_id"], two_addresses["base_id"]]

    out = await read_port.wallet_holdings("testuser", addr_ids)
    direct = await wallets.balances("testuser")  # testuser hat exakt diese zwei Adressen

    # TRX: 1000*0.20=200, USDC: 500*0.90=450 -> 650 EUR -> 65000 Cent
    assert out["value_minor"] == 65000
    assert out["currency"] == "EUR"
    assert out["complete"] is True
    from decimal import ROUND_HALF_EVEN, Decimal
    expected_minor = int((Decimal(str(direct["total"])) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_EVEN))
    assert out["value_minor"] == expected_minor


async def test_wallet_holdings_teilmenge_adressen(client, two_addresses, monkeypatch):
    """Nur EINE der beiden Adressen angegeben -> nur deren Bestand/Wert."""
    _mock_balances(monkeypatch)
    out = await read_port.wallet_holdings("testuser", [two_addresses["tron_id"]])
    assert out["value_minor"] == 20000  # nur TRX: 1000*0.20 = 200 EUR
    assert len(out["addresses"]) == 1
    assert out["addresses"][0]["id"] == two_addresses["tron_id"]
    assert all(h["chain"] == "tron" for h in out["holdings"])


async def test_wallet_holdings_form_der_holdings(client, two_addresses, monkeypatch):
    _mock_balances(monkeypatch)
    out = await read_port.wallet_holdings("testuser", [two_addresses["tron_id"]])
    h = out["holdings"][0]
    assert set(h.keys()) == {"chain", "address_id", "symbol", "coin_id", "quantity", "value_minor", "verified"}
    assert h["symbol"] == "TRX" and h["coin_id"] == "tron"
    assert h["quantity"] == "1000.0"
    assert h["address_id"] == two_addresses["tron_id"]


async def test_wallet_holdings_complete_false_ohne_kurs(client, two_addresses, monkeypatch):
    async def fake_fetch(chain, address):
        return {"tron": [{"symbol": "TRX", "amount": 1000.0, "coin_id": "tron"}]}.get(chain, [])

    async def fake_markets(vs, *, ids=None, top=None):
        return []  # kein Kurs lieferbar

    monkeypatch.setattr(chain_clients, "fetch_balance", fake_fetch)
    monkeypatch.setattr(cg, "markets", fake_markets)

    out = await read_port.wallet_holdings("testuser", [two_addresses["tron_id"]])
    assert out["complete"] is False
    assert out["holdings"][0]["value_minor"] is None


async def test_wallet_holdings_netzfehler_wirft_unavailable(client, two_addresses, monkeypatch):
    async def fake_fetch(chain, address):
        raise RuntimeError("boom")

    monkeypatch.setattr(chain_clients, "fetch_balance", fake_fetch)
    # chain_clients.fetch_balance faengt selbst Exceptions ab (siehe Docstring) -> simulieren wir
    # einen Fehler NACH diesem Punkt, direkt in wallets.balances_for_addresses's Preisabruf.
    async def fake_markets(vs, *, ids=None, top=None):
        raise RuntimeError("coingecko down")

    monkeypatch.setattr(cg, "markets", fake_markets)
    # _coin_prices faengt Exceptions intern ab -> liefert {} statt zu werfen (siehe wallets.py).
    # Fuer einen ECHTEN Ausfall muss der Fehler aus wallets.balances_for_addresses selbst kommen:
    import backend.wallets as wallets_mod

    async def broken_balances(addrs):
        raise RuntimeError("unerwarteter Fehler in balances_for_addresses")

    monkeypatch.setattr(wallets_mod, "balances_for_addresses", broken_balances)
    with pytest.raises(read_port.PortfolioUnavailable):
        await read_port.wallet_holdings("testuser", [two_addresses["tron_id"]])


# ---------------------------------------------------------------- PORT_VERSION
def test_port_version_ist_3():
    assert read_port.PORT_VERSION == 3
