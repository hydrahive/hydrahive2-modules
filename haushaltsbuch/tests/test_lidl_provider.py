from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qs

import httpx
import pytest

from backend.loyalty_provider import (
    AuthRequired,
    ForbiddenOrBlocked,
    ProviderConnection,
    ProviderUnavailable,
    RateLimited,
    SchemaChanged,
)
from backend.providers.lidl import LidlPlusProvider
from hydrahive.credentials.models import Credential
from hydrahive.credentials.store import get_credential, save_credential


def _connection() -> ProviderConnection:
    return ProviderConnection(
        7, 3, "lidl_plus", "lidl-provider-test", "owner", "DE", "de"
    )


def test_lidl_provider_refreshes_rotates_and_reads_receipt_without_writes():
    assert save_credential(
        "owner", Credential("lidl-provider-test", "bearer", "old-refresh")
    )[0]
    requests: list[tuple[str, str]] = []
    device_ids: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append((request.method, str(request.url)))
        if request.url.host == "accounts.lidl.com":
            assert request.method == "POST"
            assert request.headers["authorization"].startswith("Basic ")
            assert parse_qs(request.content.decode()) == {
                "grant_type": ["refresh_token"],
                "refresh_token": ["old-refresh"],
            }
            return httpx.Response(
                200,
                headers={"content-type": "application/json"},
                json={
                    "access_token": "short-lived-access",
                    "refresh_token": "rotated-refresh",
                    "expires_in": 300,
                },
            )
        assert request.headers["authorization"] == "Bearer short-lived-access"
        assert request.headers["app-version"] == "16.43.4"
        assert request.headers["operating-system"] == "Android"
        assert request.headers["app"] == "com.lidl.eci.lidlplus"
        assert request.headers["accept-language"] == "de"
        assert request.headers["user-agent"] == "okhttp/5.3.2"
        assert request.headers["os-version"] == "16"
        assert request.headers["model"] == "sdk_gphone64_x86_64"
        assert request.headers["brand"] == "Google"
        assert len(request.headers["deviceid"]) == 16
        int(request.headers["deviceid"], 16)
        assert parsedate_to_datetime(request.headers["date"]).utcoffset() is not None
        device_ids.append(request.headers["deviceid"])
        if request.url.path.endswith("/tickets"):
            return httpx.Response(
                200,
                headers={"content-type": "application/json"},
                json={"tickets": [{"id": "ticket-1"}], "totalCount": 1, "size": 20},
            )
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={
                "id": "ticket-1",
                "date": "2026-07-18T12:30:00+02:00",
                "totalAmount": "4,99",
                "currency": {"code": "EUR"},
                "store": {"id": "DE-1", "name": "Lidl Berlin"},
                "itemsLine": [],
            },
        )

    provider = LidlPlusProvider(transport=httpx.MockTransport(handler))
    capabilities = asyncio.run(provider.probe(_connection()))
    page = asyncio.run(provider.list_receipts(_connection(), None, 100))
    receipt = asyncio.run(provider.get_receipt(_connection(), page.items[0]))
    assert capabilities.receipts is True
    assert page.items == ["ticket-1"]
    assert receipt.total_minor == 499
    assert get_credential("owner", "lidl-provider-test").value == "rotated-refresh"
    assert [method for method, _ in requests] == ["POST", "GET", "GET"]
    assert len(set(device_ids)) == 1


def test_lidl_provider_refreshes_an_expired_primed_access_token():
    assert save_credential(
        "owner", Credential("lidl-provider-test", "bearer", "refresh")
    )[0]
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.url.host == "accounts.lidl.com"
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={
                "access_token": "renewed-access",
                "refresh_token": "renewed-refresh",
                "expires_in": 300,
            },
        )

    provider = LidlPlusProvider(transport=httpx.MockTransport(handler))
    provider.prime_auth(
        _connection().connection_id,
        "expired-access",
        datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    capabilities = asyncio.run(provider.probe(_connection()))
    assert capabilities.token_refresh is True
    assert provider._headers(_connection())["Authorization"] == "Bearer renewed-access"
    assert len(requests) == 1


def test_lidl_provider_refreshes_once_and_retries_ticket_401():
    assert save_credential(
        "owner", Credential("lidl-provider-test", "bearer", "initial-refresh")
    )[0]
    hosts: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        hosts.append(request.url.host or "")
        if request.url.host == "accounts.lidl.com":
            return httpx.Response(
                200,
                headers={"content-type": "application/json"},
                json={
                    "access_token": "refreshed-access",
                    "refresh_token": "rotated-refresh",
                    "expires_in": 300,
                },
            )
        if len(hosts) == 1:
            assert request.headers["authorization"] == "Bearer initial-access"
            return httpx.Response(
                401, headers={"content-type": "application/json"}, json={}
            )
        assert request.headers["authorization"] == "Bearer refreshed-access"
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={"tickets": [], "totalCount": 0, "size": 20},
        )

    provider = LidlPlusProvider(transport=httpx.MockTransport(handler))
    provider.prime_auth(
        _connection().connection_id,
        "initial-access",
        datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    page = asyncio.run(provider.list_receipts(_connection(), None, 100))
    assert page.items == []
    assert hosts == [
        "tickets.lidlplus.com",
        "accounts.lidl.com",
        "tickets.lidlplus.com",
    ]
    assert get_credential("owner", "lidl-provider-test").value == "rotated-refresh"


@pytest.mark.parametrize(
    ("status", "error"),
    [(401, ProviderUnavailable), (403, ForbiddenOrBlocked), (429, RateLimited)],
)
def test_lidl_provider_maps_remote_auth_and_rate_errors(status, error):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "accounts.lidl.com":
            return httpx.Response(
                200,
                headers={"content-type": "application/json"},
                json={
                    "access_token": "access",
                    "refresh_token": "refresh",
                    "expires_in": 300,
                },
            )
        return httpx.Response(
            status,
            headers={"content-type": "application/json", "retry-after": "60"},
            content=json.dumps({"error": "redacted upstream detail"}).encode(),
        )

    assert save_credential(
        "owner", Credential("lidl-provider-test", "bearer", "refresh")
    )[0]
    provider = LidlPlusProvider(transport=httpx.MockTransport(handler))
    asyncio.run(provider.probe(_connection()))
    with pytest.raises(error) as exc:
        asyncio.run(provider.list_receipts(_connection(), None, 100))
    assert "redacted upstream detail" not in str(exc.value)
    if status == 401:
        assert exc.value.code == "lidl_ticket_list_unauthorized"


def test_lidl_provider_marks_only_token_endpoint_rejection_as_reauth():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "accounts.lidl.com"
        return httpx.Response(
            401, headers={"content-type": "application/json"}, json={}
        )

    assert save_credential(
        "owner", Credential("lidl-provider-test", "bearer", "rejected-refresh")
    )[0]
    provider = LidlPlusProvider(transport=httpx.MockTransport(handler))
    with pytest.raises(AuthRequired) as exc:
        asyncio.run(provider.probe(_connection()))
    assert exc.value.code == "lidl_refresh_rejected"


def test_lidl_provider_rejects_html_and_invalid_receipt_ids():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "text/html"}, text="<html>login</html>")

    assert save_credential(
        "owner", Credential("lidl-provider-test", "bearer", "refresh")
    )[0]
    provider = LidlPlusProvider(transport=httpx.MockTransport(handler))
    with pytest.raises(SchemaChanged):
        asyncio.run(provider.refresh_auth(_connection()))
    with pytest.raises(Exception, match="receipt_id_invalid"):
        asyncio.run(provider.get_receipt(_connection(), "../token"))
