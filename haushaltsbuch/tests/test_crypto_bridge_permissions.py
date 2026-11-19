"""Rechte-Tests für die Crypto-Brücke: Mitglied B sieht As Verknüpfung nicht,
der Port wird nie mit As Username gerufen, B kann nicht importieren/
fremde Portfolios verknüpfen, Owner darf trennen, fremder Haushalt 404."""

from __future__ import annotations

from conftest import PREFIX
from test_crypto_bridge import FakePort, _install_fake_port, _link, _wallet_account
from test_v1_api import _create_account, _create_household


def _add_member(client, owner_headers, username: str) -> dict:
    response = client.post(
        f"{PREFIX}/household/members", headers=owner_headers, json={"username": username}
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_member_sees_wallet_linked_by_owner_as_hidden_without_calling_port_for_member(
    client, owner_headers, member_headers
):
    _create_household(client, owner_headers)
    _add_member(client, owner_headers, "member")
    wallet = _wallet_account(client, owner_headers)
    port = FakePort()
    port.portfolios["owner"] = [{"id": "default", "label": "Portfolio", "currency": "EUR"}]
    port.values["owner"] = {"value_minor": 12345, "as_of": "2026-01-01T00:00:00Z", "complete": True}

    import pytest

    with pytest.MonkeyPatch.context() as monkeypatch:
        _install_fake_port(monkeypatch, port)
        linked = _link(client, owner_headers, wallet).json()

        accounts_as_member = client.get(f"{PREFIX}/accounts", headers=member_headers).json()
        member_view = next(item for item in accounts_as_member if item["id"] == linked["id"])
        assert member_view["crypto_linked"] is True
        assert member_view["linked_by_me"] is False
        assert member_view["linked_portfolio_id"] is None  # keine fremde Portfolio-ID sichtbar

        calls_before = list(port.calls)
        value_as_member = client.get(
            f"{PREFIX}/accounts/{linked['id']}/crypto-value", headers=member_headers
        )
        assert value_as_member.status_code == 200
        body = value_as_member.json()
        assert body["state"] == "hidden"
        assert body["value_minor"] is None
        assert body["as_of"] is None
        # Der Port darf für Bs Anfrage NICHT aufgerufen worden sein - insbesondere
        # nie mit "owner" als Argument im Namen von B.
        assert port.calls == calls_before


def test_member_cannot_import_trades_for_owners_linked_wallet(
    client, owner_headers, member_headers
):
    _create_household(client, owner_headers)
    _add_member(client, owner_headers, "member")
    wallet = _wallet_account(client, owner_headers)
    fiat = _create_account(client, owner_headers, opening_balance=0)
    port = FakePort()
    port.portfolios["owner"] = [{"id": "default", "label": "Portfolio", "currency": "EUR"}]

    import pytest

    with pytest.MonkeyPatch.context() as monkeypatch:
        _install_fake_port(monkeypatch, port)
        _link(client, owner_headers, wallet)

        response = client.post(
            f"{PREFIX}/crypto-bridge/trade-imports",
            headers=member_headers,
            json={"wallet_account_id": wallet["id"], "fiat_account_id": fiat["id"], "since": None},
        )
        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "crypto_link_owner_only"
        # Trades dürfen für B nie abgefragt worden sein.
        assert ("trades", "owner") not in port.calls
        assert ("trades", "member") not in port.calls


def test_member_cannot_link_foreign_portfolio_id(client, owner_headers, member_headers):
    _create_household(client, owner_headers)
    _add_member(client, owner_headers, "member")
    wallet = _wallet_account(client, owner_headers, name="Member-Wallet")
    # Das Konto ist Haushaltskonto, aber "member" versucht eine Portfolio-ID
    # zu verknüpfen, die nur "owner" gehört (member hat gar kein Portfolio).
    port = FakePort()
    port.portfolios["owner"] = [{"id": "default", "label": "Portfolio", "currency": "EUR"}]
    port.portfolios["member"] = []

    import pytest

    with pytest.MonkeyPatch.context() as monkeypatch:
        _install_fake_port(monkeypatch, port)
        response = client.put(
            f"{PREFIX}/accounts/{wallet['id']}/crypto-link",
            headers=member_headers,
            json={"portfolio_id": "default", "revision": wallet["revision"]},
        )
        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "crypto_portfolio_not_found"
        # Der Port wurde für die Prüfung mit "member" aufgerufen, NICHT mit "owner".
        assert ("portfolios_for", "member") in port.calls
        assert ("portfolios_for", "owner") not in port.calls


def test_owner_may_unlink_wallet_linked_by_member(client, owner_headers, member_headers):
    _create_household(client, owner_headers)
    added = _add_member(client, owner_headers, "member")
    assert added["user_id"] == "user-member"
    wallet_response = client.post(
        f"{PREFIX}/accounts",
        headers=owner_headers,
        json={
            "name": "Gemeinsames Wallet", "type": "wallet", "currency": "EUR",
            "opening_balance": 0, "owner_member_id": added["id"],
        },
    )
    assert wallet_response.status_code == 201, wallet_response.text
    wallet = wallet_response.json()

    port = FakePort()
    port.portfolios["member"] = [{"id": "default", "label": "Portfolio", "currency": "EUR"}]

    import pytest

    with pytest.MonkeyPatch.context() as monkeypatch:
        _install_fake_port(monkeypatch, port)
        linked = _link(client, member_headers, wallet).json()
        assert linked["linked_by_me"] is True

        # Owner (nicht der Verknüpfer selbst) darf trennen.
        unlinked = client.delete(
            f"{PREFIX}/accounts/{linked['id']}/crypto-link?revision={linked['revision']}",
            headers=owner_headers,
        )
        assert unlinked.status_code == 200, unlinked.text
        assert unlinked.json()["crypto_linked"] is False


def test_foreign_household_gets_404_on_all_crypto_bridge_endpoints(
    client, owner_headers, outsider_headers
):
    _create_household(client, owner_headers)
    wallet = _wallet_account(client, owner_headers)
    port = FakePort()
    port.portfolios["owner"] = [{"id": "default", "label": "Portfolio", "currency": "EUR"}]

    import pytest

    with pytest.MonkeyPatch.context() as monkeypatch:
        _install_fake_port(monkeypatch, port)

        status_response = client.get(f"{PREFIX}/crypto-bridge/status", headers=outsider_headers)
        assert status_response.status_code == 404
        assert status_response.json()["detail"]["code"] == "household_not_found"

        link_response = client.put(
            f"{PREFIX}/accounts/{wallet['id']}/crypto-link",
            headers=outsider_headers,
            json={"portfolio_id": "default", "revision": wallet["revision"]},
        )
        assert link_response.status_code == 404
        assert link_response.json()["detail"]["code"] == "household_not_found"

        value_response = client.get(
            f"{PREFIX}/accounts/{wallet['id']}/crypto-value", headers=outsider_headers
        )
        assert value_response.status_code == 404
        assert value_response.json()["detail"]["code"] == "household_not_found"

        trade_response = client.post(
            f"{PREFIX}/crypto-bridge/trade-imports",
            headers=outsider_headers,
            json={"wallet_account_id": wallet["id"], "fiat_account_id": wallet["id"], "since": None},
        )
        assert trade_response.status_code == 404
        assert trade_response.json()["detail"]["code"] == "household_not_found"
