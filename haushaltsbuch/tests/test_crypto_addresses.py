"""Tests für die Crypto-Brücke v2 (Etappe A1/A2, VERTRAG-PORT-V2.md): Konto <->
Adressen (statt nur Portfolio), Bestand je Coin + EUR-Wert.

Nutzt denselben Fake-Port wie test_crypto_bridge.py (monkeypatch von
`crypto_bridge._load_port`) - kein echtes cryptoboard-Modul nötig.
"""

from __future__ import annotations

from backend import crypto_bridge
from conftest import PREFIX
from test_crypto_bridge import FakePort, _fake_port_version, _install_fake_port, _wallet_account
from test_v1_api import _create_account, _create_household


def _link_addr(client, headers, account: dict, address_ids: list[int]):
    return client.put(
        f"{PREFIX}/accounts/{account['id']}/crypto-addresses",
        headers=headers,
        json={"address_ids": address_ids, "revision": account["revision"]},
    )


def _holdings(client, headers, account_id: int):
    return client.get(f"{PREFIX}/accounts/{account_id}/crypto-holdings", headers=headers)


def _basic_holdings_result(username: str = "owner") -> dict:
    return {
        "currency": "EUR", "as_of": "2026-11-20T10:00:00Z", "complete": True, "value_minor": 123456,
        "addresses": [{"id": 2, "chain": "base", "address": "0xa1aE696E", "label": "Base"}],
        "holdings": [
            {"chain": "base", "address_id": 2, "symbol": "USDC", "coin_id": "usd-coin",
             "quantity": "100.5", "value_minor": 100500, "verified": True},
        ],
    }


# ---------------------------------------------------------------------------
# GET /crypto-bridge/addresses
# ---------------------------------------------------------------------------


def test_get_addresses_marks_linked_account(client, owner_headers, monkeypatch):
    _create_household(client, owner_headers)
    wallet = _wallet_account(client, owner_headers)
    port = FakePort()
    port.addresses["owner"] = [
        {"id": 2, "chain": "base", "address": "0xa1aE696E", "label": "Base"},
        {"id": 3, "chain": "tron", "address": "TWgdivZeyD", "label": "Tron"},
    ]
    _install_fake_port(monkeypatch, port)

    linked = _link_addr(client, owner_headers, wallet, [2]).json()
    assert linked["crypto_addresses"] == [{"address_id": 2, "chain": "base", "address_short": "0xa1aE…696E"}]

    addresses = client.get(f"{PREFIX}/crypto-bridge/addresses", headers=owner_headers).json()
    by_id = {a["id"]: a for a in addresses}
    assert by_id[2]["linked_account_id"] == wallet["id"]
    assert by_id[3]["linked_account_id"] is None


# ---------------------------------------------------------------------------
# Verknüpfen / Ersetzen / Lösen
# ---------------------------------------------------------------------------


def test_link_requires_wallet_type(client, owner_headers, monkeypatch):
    _create_household(client, owner_headers)
    checking = _create_account(client, owner_headers)
    port = FakePort()
    port.addresses["owner"] = [{"id": 2, "chain": "base", "address": "0xabc", "label": ""}]
    _install_fake_port(monkeypatch, port)

    response = _link_addr(client, owner_headers, checking, [2])
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "crypto_wallet_required"


def test_link_rejects_foreign_address_id(client, owner_headers, monkeypatch):
    """Der Port kennt die Adresse nicht (gehört nicht owner) -> 404, kein Leak."""
    _create_household(client, owner_headers)
    wallet = _wallet_account(client, owner_headers)
    port = FakePort()
    port.addresses["owner"] = [{"id": 2, "chain": "base", "address": "0xabc", "label": ""}]
    _install_fake_port(monkeypatch, port)

    response = _link_addr(client, owner_headers, wallet, [999])
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "crypto_address_not_found"


def test_link_two_addresses_same_user_one_account_base_ethereum(client, owner_headers, monkeypatch):
    """Base + Ethereum (gleiche 0x-Adresse) als EIN Konto - mehrere Adressen
    je Konto sind erlaubt (Vertrag)."""
    _create_household(client, owner_headers)
    wallet = _wallet_account(client, owner_headers, name="Base/Ethereum")
    port = FakePort()
    port.addresses["owner"] = [
        {"id": 2, "chain": "base", "address": "0xa1aE696E", "label": "Base"},
        {"id": 7, "chain": "ethereum", "address": "0xa1aE696E", "label": "Ethereum"},
    ]
    _install_fake_port(monkeypatch, port)

    linked = _link_addr(client, owner_headers, wallet, [2, 7]).json()
    assert {a["address_id"] for a in linked["crypto_addresses"]} == {2, 7}
    assert linked["revision"] == wallet["revision"] + 1


def test_address_already_linked_to_other_account_is_409(client, owner_headers, monkeypatch):
    _create_household(client, owner_headers)
    wallet_a = _wallet_account(client, owner_headers, name="Wallet A")
    wallet_b = _wallet_account(client, owner_headers, name="Wallet B")
    port = FakePort()
    port.addresses["owner"] = [{"id": 2, "chain": "base", "address": "0xabc", "label": ""}]
    _install_fake_port(monkeypatch, port)

    assert _link_addr(client, owner_headers, wallet_a, [2]).status_code == 200
    response = _link_addr(client, owner_headers, wallet_b, [2])
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "crypto_address_already_linked"


def test_replace_addresses_then_unlink(client, owner_headers, monkeypatch):
    _create_household(client, owner_headers)
    wallet = _wallet_account(client, owner_headers)
    port = FakePort()
    port.addresses["owner"] = [
        {"id": 2, "chain": "base", "address": "0xabc", "label": ""},
        {"id": 3, "chain": "tron", "address": "Txyz", "label": ""},
    ]
    _install_fake_port(monkeypatch, port)

    linked = _link_addr(client, owner_headers, wallet, [2]).json()
    replaced = _link_addr(client, owner_headers, wallet, [3]).json()
    assert {a["address_id"] for a in replaced["crypto_addresses"]} == {3}

    unlinked = client.delete(
        f"{PREFIX}/accounts/{wallet['id']}/crypto-addresses?revision={replaced['revision']}",
        headers=owner_headers,
    )
    assert unlinked.status_code == 200, unlinked.text
    assert unlinked.json()["crypto_addresses"] == []

    second_unlink = client.delete(
        f"{PREFIX}/accounts/{wallet['id']}/crypto-addresses?revision={unlinked.json()['revision']}",
        headers=owner_headers,
    )
    assert second_unlink.status_code == 409
    assert second_unlink.json()["detail"]["code"] == "crypto_account_not_linked"


# ---------------------------------------------------------------------------
# GET /accounts (Kontoliste zeigt verknüpfte Adressen)
# ---------------------------------------------------------------------------


def test_account_list_shows_linked_addresses_for_wallet(client, owner_headers, monkeypatch):
    _create_household(client, owner_headers)
    wallet = _wallet_account(client, owner_headers)
    checking = _create_account(client, owner_headers)
    port = FakePort()
    port.addresses["owner"] = [{"id": 3, "chain": "tron", "address": "TWgdivZeyD", "label": ""}]
    _install_fake_port(monkeypatch, port)
    _link_addr(client, owner_headers, wallet, [3])

    accounts = client.get(f"{PREFIX}/accounts", headers=owner_headers).json()
    wallet_view = next(a for a in accounts if a["id"] == wallet["id"])
    checking_view = next(a for a in accounts if a["id"] == checking["id"])
    assert wallet_view["crypto_addresses"] == [{"address_id": 3, "chain": "tron", "address_short": "TWgdiv…ZeyD"}]
    assert checking_view["crypto_addresses"] == []


# ---------------------------------------------------------------------------
# GET /accounts/{id}/crypto-holdings
# ---------------------------------------------------------------------------


def test_holdings_unlinked_account(client, owner_headers, monkeypatch):
    _create_household(client, owner_headers)
    wallet = _wallet_account(client, owner_headers)
    _install_fake_port(monkeypatch, FakePort())

    response = _holdings(client, owner_headers, wallet["id"])
    assert response.status_code == 200
    assert response.json()["state"] == "unlinked"


def test_holdings_live_integer_cent_and_string_quantities(client, owner_headers, monkeypatch):
    _create_household(client, owner_headers)
    wallet = _wallet_account(client, owner_headers)
    port = FakePort()
    port.addresses["owner"] = [{"id": 2, "chain": "base", "address": "0xabc", "label": ""}]
    port.holdings["owner"] = _basic_holdings_result()
    _install_fake_port(monkeypatch, port)
    linked = _link_addr(client, owner_headers, wallet, [2]).json()

    response = _holdings(client, owner_headers, linked["id"])
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "live"
    assert body["value_minor"] == 123456
    assert type(body["value_minor"]) is int
    assert body["holdings"][0]["quantity"] == "100.5"
    assert type(body["holdings"][0]["quantity"]) is str
    assert body["holdings"][0]["value_minor"] == 100500
    assert body["complete"] is True


def test_holdings_port_unavailable_falls_back_to_stale_snapshot(client, owner_headers, monkeypatch):
    _create_household(client, owner_headers)
    wallet = _wallet_account(client, owner_headers)
    port = FakePort()
    port.addresses["owner"] = [{"id": 2, "chain": "base", "address": "0xabc", "label": ""}]
    port.holdings["owner"] = _basic_holdings_result()
    _install_fake_port(monkeypatch, port)
    linked = _link_addr(client, owner_headers, wallet, [2]).json()
    live = _holdings(client, owner_headers, linked["id"])
    assert live.json()["state"] == "live"

    def _raise_missing():
        raise crypto_bridge.CryptoBridgeUnavailable("module_missing")

    monkeypatch.setattr(crypto_bridge, "_load_port", _raise_missing)
    stale = _holdings(client, owner_headers, linked["id"])
    assert stale.status_code == 200
    body = stale.json()
    assert body["state"] == "stale"
    assert body["value_minor"] == 123456
    assert body["holdings"] == _basic_holdings_result()["holdings"]
    assert body["reason"] == "module_missing"


def test_holdings_port_v1_is_port_incompatible(client, owner_headers, monkeypatch):
    """Port meldet noch PORT_VERSION 1 (nicht upgegradet) -> stale/port_incompatible,
    kein 500."""
    _create_household(client, owner_headers)
    wallet = _wallet_account(client, owner_headers)
    port_v2 = FakePort()
    port_v2.addresses["owner"] = [{"id": 2, "chain": "base", "address": "0xabc", "label": ""}]
    _install_fake_port(monkeypatch, port_v2)
    linked = _link_addr(client, owner_headers, wallet, [2]).json()

    def _raise_incompatible():
        raise crypto_bridge.CryptoBridgeUnavailable("port_incompatible")

    monkeypatch.setattr(crypto_bridge, "_load_port", _raise_incompatible)
    response = _holdings(client, owner_headers, linked["id"])
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "stale"
    assert body["reason"] == "port_incompatible"


def test_holdings_foreign_address_id_not_found(client, owner_headers, monkeypatch):
    """Der Port kennt die address_id des Kontos nicht mehr (z.B. gelöscht) ->
    404, kein 500."""
    _create_household(client, owner_headers)
    wallet = _wallet_account(client, owner_headers)
    port = FakePort()
    port.addresses["owner"] = [{"id": 2, "chain": "base", "address": "0xabc", "label": ""}]
    _install_fake_port(monkeypatch, port)
    linked = _link_addr(client, owner_headers, wallet, [2]).json()

    # Adresse beim Port "verschwindet" (z.B. zwischenzeitlich gelöscht) -
    # das Konto hat die address_id noch verknüpft, der Port nicht mehr.
    port.addresses["owner"] = []
    response = _holdings(client, owner_headers, linked["id"])
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "crypto_address_not_found"
