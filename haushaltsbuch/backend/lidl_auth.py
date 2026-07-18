"""Benutzergeführter Lidl-OIDC-PKCE-Flow ohne Passwort- oder MFA-Übertragung."""
from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlencode, urlparse

from hydrahive.api.middleware.auth import AuthPrincipal
from hydrahive.credentials.models import Credential
from hydrahive.credentials.store import delete_credential, save_credential
from .lidl_config import (
    AUTH_URL, CLIENT_ID, REDIRECT_URI, SCOPE, TOKEN_URL, USERINFO_URL, enabled,
    token_headers,
)
from .lidl_flow import (
    AuthFlowError, InvalidFlow, pkce_challenge, read_flow, seal_flow,
)
from .lidl_flow_store import claim_flow, create_flow_record, finish_flow
from .lidl_http import request_json
from .loyalty_connections import create_connection, enable_experimental
from .loyalty_provider import (
    AuthRequired, ForbiddenOrBlocked, ProviderError, RateLimited,
)
from .loyalty_requests import LidlAuthComplete, LidlAuthStart, LoyaltyConnectionCreate

FLOW_TTL = timedelta(minutes=10)


@dataclass(frozen=True, slots=True)
class ExchangeResult:
    refresh_token: str
    account_id: str
    masked_account: str

def parse_callback(callback_url: str, expected_state: str) -> str:
    parsed = urlparse(callback_url)
    try:
        port = parsed.port
    except ValueError as exc:
        raise AuthFlowError("lidl_callback_invalid") from exc
    if (
        parsed.scheme != "com.lidlplus.app" or parsed.netloc != "callback"
        or parsed.hostname != "callback" or parsed.path or parsed.params or parsed.fragment
        or parsed.username or parsed.password or port is not None
    ):
        raise AuthFlowError("lidl_callback_invalid")
    try:
        query = parse_qs(parsed.query, keep_blank_values=True, strict_parsing=True)
    except ValueError as exc:
        raise AuthFlowError("lidl_callback_invalid") from exc
    if set(query) - {"code", "state", "session_state", "iss"}:
        raise AuthFlowError("lidl_callback_invalid")
    if "iss" in query and query["iss"] != ["https://accounts.lidl.com"]:
        raise AuthFlowError("lidl_callback_invalid")
    if len(query.get("code", [])) != 1 or len(query.get("state", [])) != 1:
        raise AuthFlowError("lidl_callback_invalid")
    if not query["code"][0] or not secrets.compare_digest(query["state"][0], expected_state):
        raise AuthFlowError("lidl_callback_invalid")
    return query["code"][0]


def start_auth(body: LidlAuthStart, principal: AuthPrincipal) -> dict:
    del body
    if not enabled():
        raise AuthFlowError("lidl_feature_disabled", 503)
    now, flow_id = datetime.now(timezone.utc), secrets.token_urlsafe(24)
    state, nonce, verifier = (secrets.token_urlsafe(size) for size in (32, 32, 64))
    challenge = pkce_challenge(verifier)
    expires_at = now + FLOW_TTL
    household_id, member_id = create_flow_record(
        principal, flow_id, SCOPE, expires_at
    )
    flow = {
        "flow_id": flow_id, "household_id": household_id, "member_id": member_id,
        "state": state, "nonce": nonce, "verifier": verifier, "expires_at": expires_at.isoformat(),
    }
    query = urlencode({
        "client_id": CLIENT_ID, "response_type": "code", "redirect_uri": REDIRECT_URI,
        "scope": SCOPE, "state": state, "nonce": nonce, "code_challenge": challenge,
        "code_challenge_method": "S256", "ui_locales": "de-DE",
        "Country": "DE", "language": "de-DE",
    })
    return {
        "authorization_url": f"{AUTH_URL}?{query}",
        "flow_token": seal_flow(flow),
        "expires_at": expires_at.isoformat(),
    }


def _read_flow(token: str) -> dict:
    try:
        return read_flow(token)
    except InvalidFlow as exc:
        raise AuthFlowError("lidl_auth_flow_invalid") from exc


async def _exchange_code(code: str, verifier: str, nonce: str) -> ExchangeResult:
    del nonce  # Nonce wird nur für ein optionales ID-Token gesendet; Identität kommt von Userinfo.
    try:
        payload = await request_json("POST", TOKEN_URL, headers=token_headers(), data={
            "grant_type": "authorization_code", "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI, "code": code, "code_verifier": verifier,
        })
        if not isinstance(payload, dict):
            raise AuthFlowError("lidl_token_invalid")
        refresh, access = payload.get("refresh_token"), payload.get("access_token")
        if not all(isinstance(value, str) and 0 < len(value) <= 16_384 for value in (refresh, access)):
            raise AuthFlowError("lidl_token_invalid")
        profile = await request_json(
            "GET", USERINFO_URL, headers={"Authorization": f"Bearer {access}"}
        )
    except RateLimited as exc:
        raise AuthFlowError("lidl_auth_rate_limited", 429) from exc
    except (AuthRequired, ForbiddenOrBlocked) as exc:
        raise AuthFlowError("lidl_auth_failed") from exc
    except ProviderError as exc:
        raise AuthFlowError("lidl_auth_unavailable", 502) from exc
    account_id = profile.get("sub") if isinstance(profile, dict) else None
    if not isinstance(account_id, str) or not account_id or len(account_id) > 256:
        raise AuthFlowError("lidl_token_invalid")
    return ExchangeResult(refresh, account_id, "Lidl Plus")


async def complete_auth(body: LidlAuthComplete, principal: AuthPrincipal) -> dict:
    if not enabled():
        raise AuthFlowError("lidl_feature_disabled", 503)
    flow = _read_flow(body.flow_token)
    code = parse_callback(body.callback_url, flow["state"])
    claim_flow(flow, principal, SCOPE)
    try:
        result = await _exchange_code(code, flow["verifier"], flow["nonce"])
    except Exception:
        finish_flow(flow, consumed=False)
        raise
    finish_flow(flow, consumed=True)
    credential_ref = f"lidl-{flow['member_id']}-{secrets.token_hex(5)}"
    ok, _ = save_credential(principal.username, Credential(
        name=credential_ref, type="bearer", value=result.refresh_token,
        url_pattern="https://*.lidlplus.com/*", description="Lidl Plus refresh token",
    ))
    if not ok:
        raise AuthFlowError("lidl_credential_save_failed", 500)
    try:
        connection = create_connection(LoyaltyConnectionCreate(
            provider="lidl_plus", credential_ref=credential_ref,
            provider_account_id=result.account_id, masked_account=result.masked_account,
            alias=body.alias, country_code="DE", language_code="de",
            visibility=body.visibility,
        ), principal)
        return enable_experimental(connection["id"], principal)
    except Exception:
        delete_credential(principal.username, credential_ref)
        raise
