"""Aktueller Android-Client für Lidls read-only Ticket-API."""
from __future__ import annotations

import hashlib
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from email.utils import format_datetime

import httpx

from .lidl_config import APP_VERSION
from .lidl_http import request_json
from .loyalty_provider import (
    AuthRequired, ProviderConnection, ProviderUnavailable, TokenMetadata,
)


def ticket_headers(access_token: str, connection: ProviderConnection) -> dict[str, str]:
    device_seed = (
        f"hydrahive-lidl:{connection.credential_owner}:{connection.credential_ref}"
    ).encode()
    device_id = hashlib.sha256(device_seed).hexdigest()[:16]
    return {
        "Authorization": f"Bearer {access_token}",
        "App-Version": APP_VERSION,
        "Operating-System": "Android",
        "App": "com.lidl.eci.lidlplus",
        "Accept-Language": connection.language_code,
        "User-Agent": "okhttp/5.3.2",
        "OS-Version": "16",
        "Model": "sdk_gphone64_x86_64",
        "Brand": "Google",
        "deviceid": device_id,
        "Date": format_datetime(datetime.now(timezone.utc), usegmt=True),
    }


async def request_ticket_json(
    url: str,
    connection: ProviderConnection,
    headers_for: Callable[[ProviderConnection], dict[str, str]],
    refresh_auth: Callable[[ProviderConnection], Awaitable[TokenMetadata]],
    transport: httpx.AsyncBaseTransport | None,
    unauthorized_code: str,
) -> dict | list:
    try:
        return await request_json(
            "GET", url, headers=headers_for(connection), transport=transport
        )
    except AuthRequired:
        await refresh_auth(connection)
    try:
        return await request_json(
            "GET", url, headers=headers_for(connection), transport=transport
        )
    except AuthRequired as exc:
        raise ProviderUnavailable(unauthorized_code) from exc
