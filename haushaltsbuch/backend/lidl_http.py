"""Begrenzter HTTPS-JSON-Transport ausschließlich zu festen Lidl-Hosts."""
from __future__ import annotations

import json
from decimal import Decimal
from urllib.parse import urlparse

import httpx

from .loyalty_provider import (
    AuthRequired, ForbiddenOrBlocked, ProviderUnavailable, RateLimited, SchemaChanged,
)

ALLOWED_HOSTS = frozenset({"accounts.lidl.com", "tickets.lidlplus.com", "profile.lidlplus.com"})
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
TIMEOUT = httpx.Timeout(20.0, connect=5.0, read=15.0, write=10.0, pool=5.0)


def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS or parsed.fragment:
        raise ProviderUnavailable("lidl_host_not_allowed")
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ProviderUnavailable("lidl_url_invalid")


def _status(response: httpx.Response) -> None:
    if response.status_code == 401:
        raise AuthRequired()
    if response.status_code == 403:
        raise ForbiddenOrBlocked()
    if response.status_code == 429:
        value = response.headers.get("retry-after", "")
        raise RateLimited(int(value) if value.isdigit() else None)
    if response.status_code >= 500:
        raise ProviderUnavailable()
    if response.status_code >= 400:
        raise AuthRequired() if response.status_code == 400 else ProviderUnavailable()


async def request_json(
    method: str, url: str, *, headers: dict | None = None, data: dict | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> dict | list:
    if method not in {"GET", "POST"}:
        raise ProviderUnavailable("lidl_method_not_allowed")
    _validate_url(url)
    try:
        async with httpx.AsyncClient(
            timeout=TIMEOUT, verify=True, follow_redirects=False, transport=transport
        ) as client:
            async with client.stream(method, url, headers=headers, data=data) as response:
                _status(response)
                content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
                if content_type != "application/json":
                    raise SchemaChanged("unexpected_content_type")
                chunks, size = [], 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > MAX_RESPONSE_BYTES:
                        raise SchemaChanged("response_too_large")
                    chunks.append(chunk)
    except httpx.HTTPError as exc:
        raise ProviderUnavailable() from exc
    try:
        value = json.loads(b"".join(chunks), parse_float=Decimal)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SchemaChanged("invalid_json") from exc
    if not isinstance(value, (dict, list)):
        raise SchemaChanged("invalid_json_shape")
    return value
