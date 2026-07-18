from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest

from backend import lidl_auth
from backend.lidl_auth import ExchangeResult
from conftest import PREFIX
from test_v1_api import _create_household


def _start(client, headers):
    return client.post(
        f"{PREFIX}/loyalty/lidl/auth/start", headers=headers,
        json={"accepted_experimental_risk": True, "country_code": "DE", "language_code": "de"},
    )


def test_start_requires_explicit_risk_and_builds_fixed_s256_url(client, owner_headers):
    _create_household(client, owner_headers)
    denied = client.post(
        f"{PREFIX}/loyalty/lidl/auth/start", headers=owner_headers,
        json={"accepted_experimental_risk": False, "country_code": "DE", "language_code": "de"},
    )
    assert denied.status_code == 422
    started = _start(client, owner_headers)
    assert started.status_code == 200, started.text
    body = started.json()
    parsed = urlparse(body["authorization_url"])
    query = parse_qs(parsed.query)
    assert (parsed.scheme, parsed.hostname, parsed.path) == ("https", "accounts.lidl.com", "/connect/authorize")
    assert query["client_id"] == ["LidlPlusNativeClient"]
    assert query["redirect_uri"] == ["com.lidlplus.app://callback"]
    assert query["scope"] == ["openid profile offline_access lpprofile lpapis"]
    assert query["code_challenge_method"] == ["S256"]
    assert query["Country"] == ["DE"]
    assert query["language"] == ["de-DE"]
    assert body["flow_token"].startswith("enc:v1:")

    from hydrahive.db.connection import db
    with db() as conn:
        row = conn.execute("SELECT * FROM module_haushaltsbuch_loyalty_auth_flows").fetchone()
    serialized = " ".join(map(str, row))
    assert query["state"][0] not in serialized
    assert "code_verifier" not in serialized


def test_complete_validates_exact_callback_state_and_prevents_replay(
    client, owner_headers, monkeypatch
):
    _create_household(client, owner_headers)
    started = _start(client, owner_headers).json()
    state = parse_qs(urlparse(started["authorization_url"]).query)["state"][0]

    async def exchange(code, verifier, nonce):
        assert code == "authorization-code"
        assert len(verifier) >= 43
        return ExchangeResult("refresh-secret", "account-123", "Lidl ****0123")

    monkeypatch.setattr(lidl_auth, "_exchange_code", exchange)
    invalid = client.post(
        f"{PREFIX}/loyalty/lidl/auth/complete", headers=owner_headers,
        json={"flow_token": started["flow_token"], "callback_url": f"https://callback?code=x&state={state}"},
    )
    assert invalid.status_code == 400
    assert invalid.json()["detail"]["code"] == "lidl_callback_invalid"

    from hydrahive.credentials.store import list_credentials
    before_credentials = {item.name for item in list_credentials("owner")}
    complete = client.post(
        f"{PREFIX}/loyalty/lidl/auth/complete", headers=owner_headers,
        json={
            "flow_token": started["flow_token"],
            "callback_url": f"com.lidlplus.app://callback?code=authorization-code&state={state}",
            "alias": "Mein Lidl", "visibility": "household",
        },
    )
    assert complete.status_code == 200, complete.text
    assert complete.json()["provider"] == "lidl_plus"
    assert complete.json()["feature_enabled"] is True
    assert complete.json()["status"] == "active"
    assert "credential_ref" not in complete.json()
    assert "refresh-secret" not in complete.text

    replay = client.post(
        f"{PREFIX}/loyalty/lidl/auth/complete", headers=owner_headers,
        json={"flow_token": started["flow_token"], "callback_url": f"com.lidlplus.app://callback?code=x&state={state}"},
    )
    assert replay.status_code == 409
    assert replay.json()["detail"]["code"] == "lidl_auth_flow_consumed"

    from hydrahive.credentials.store import get_credential
    connection = complete.json()
    after_credentials = {item.name for item in list_credentials("owner")}
    managed_refs = after_credentials - before_credentials
    assert len(managed_refs) == 1
    removed = client.delete(
        f"{PREFIX}/loyalty/connections/{connection['id']}?revision={connection['revision']}",
        headers=owner_headers,
    )
    assert removed.status_code == 204
    assert get_credential("owner", managed_refs.pop()) is None


def test_kill_switch_blocks_new_auth_flows(client, owner_headers, monkeypatch):
    _create_household(client, owner_headers)
    for value in ("0", "unexpected-typo"):
        monkeypatch.setenv("HH_HAUSHALTSBUCH_LIDL_ENABLED", value)
        response = _start(client, owner_headers)
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "lidl_feature_disabled"
        status = client.get(f"{PREFIX}/loyalty/provider-status", headers=owner_headers)
        assert status.json()["lidl_plus"]["enabled"] is False


def test_start_is_rate_limited_per_member(client, owner_headers):
    _create_household(client, owner_headers)
    responses = [_start(client, owner_headers) for _ in range(6)]
    assert [response.status_code for response in responses] == [200, 200, 200, 200, 200, 429]
    assert responses[-1].json()["detail"]["code"] == "lidl_auth_rate_limited"


def test_failed_exchange_releases_flow_for_one_retry(client, owner_headers, monkeypatch):
    _create_household(client, owner_headers)
    started = _start(client, owner_headers).json()
    state = parse_qs(urlparse(started["authorization_url"]).query)["state"][0]
    calls = 0

    async def exchange(code, verifier, nonce):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise lidl_auth.AuthFlowError("lidl_auth_unavailable", 502)
        return ExchangeResult("retry-refresh", "retry-account", "Lidl Plus")

    monkeypatch.setattr(lidl_auth, "_exchange_code", exchange)
    body = {
        "flow_token": started["flow_token"],
        "callback_url": f"com.lidlplus.app://callback?code=retry-code&state={state}",
    }
    first = client.post(f"{PREFIX}/loyalty/lidl/auth/complete", headers=owner_headers, json=body)
    second = client.post(f"{PREFIX}/loyalty/lidl/auth/complete", headers=owner_headers, json=body)
    assert first.status_code == 502
    assert second.status_code == 200


def test_exchange_uses_fixed_native_client_and_verified_userinfo(monkeypatch):
    calls = []

    async def request(method, url, **kwargs):
        calls.append((method, url, kwargs))
        if url.endswith("/connect/token"):
            assert kwargs["headers"]["Authorization"].startswith("Basic ")
            assert kwargs["data"]["code_verifier"] == "verifier"
            return {
                "access_token": "short-access",
                "refresh_token": "refresh-secret",
            }
        assert url.endswith("/connect/userinfo")
        assert kwargs["headers"]["Authorization"] == "Bearer short-access"
        return {"sub": "account-123"}

    monkeypatch.setattr(lidl_auth, "request_json", request)
    result = __import__("asyncio").run(
        lidl_auth._exchange_code("code", "verifier", "nonce")
    )
    assert result.account_id == "account-123"
    assert result.refresh_token == "refresh-secret"
    assert len(calls) == 2


def test_callback_rejects_duplicate_values_and_state_mismatch(client, owner_headers):
    _create_household(client, owner_headers)
    started = _start(client, owner_headers).json()
    state = parse_qs(urlparse(started["authorization_url"]).query)["state"][0]
    for callback in (
        f"com.lidlplus.app://callback/path?code=x&state={state}",
        f"com.lidlplus.app://callback?code=x&code=y&state={state}",
        "com.lidlplus.app://callback?code=x&state=wrong",
        f"com.lidlplus.app://callback?code=x&state={state}&broken",
    ):
        with pytest.raises(lidl_auth.AuthFlowError):
            lidl_auth.parse_callback(callback, state)
    plaintext = client.post(
        f"{PREFIX}/loyalty/lidl/auth/complete", headers=owner_headers,
        json={
            "flow_token": '{"flow_id":"plaintext-legacy"}',
            "callback_url": f"com.lidlplus.app://callback?code=x&state={state}",
        },
    )
    assert plaintext.status_code == 400
    assert plaintext.json()["detail"]["code"] == "lidl_auth_flow_invalid"
