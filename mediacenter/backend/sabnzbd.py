from __future__ import annotations

import asyncio
import json
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx

from hydrahive.net.ssrf import SsrfBlocked, pin_request, resolve_internal_ip

from .config import SAB_MAX_JSON_BYTES, SAB_TIMEOUT_SECONDS
from .errors import SabAuthError, SabResponseError, SabUnavailable
from .sab_credentials import SabConnection


class _SabSecretTransport(httpx.AsyncBaseTransport):
    """Injiziert den SAB-Key nur in die gepinnte Wire-Request."""

    def __init__(
        self,
        connection: SabConnection,
        pinned_ip: str,
        inner: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = connection.api_key
        self._expected = httpx.URL(f"{connection.origin}/api")
        self._pinned_ip = pinned_ip
        self._inner = inner or httpx.AsyncHTTPTransport()

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if (
            request.url.scheme != self._expected.scheme
            or request.url.host != self._expected.host
            or request.url.port != self._expected.port
            or request.url.path != "/api"
        ):
            raise SabResponseError("sab_origin_rejected")
        wire = httpx.Request(
            method=request.method,
            url=request.url.copy_merge_params({"apikey": self._api_key}),
            headers=request.headers,
            stream=request.stream,
            extensions=dict(request.extensions),
        )
        pin_request(wire, {self._expected.host: self._pinned_ip})
        return await self._inner.handle_async_request(wire)

    async def aclose(self) -> None:
        await self._inner.aclose()


async def resolve_pinned_ip(connection: SabConnection) -> str:
    host = httpx.URL(connection.origin).host
    try:
        async with asyncio.timeout(SAB_TIMEOUT_SECONDS):
            return await asyncio.to_thread(resolve_internal_ip, host)
    except (OSError, SsrfBlocked, TimeoutError):
        pass
    raise SabUnavailable("sab_unavailable")


@asynccontextmanager
async def _client(
    connection: SabConnection,
    *,
    inner_transport: httpx.AsyncBaseTransport | None = None,
    pinned_ip: str | None = None,
) -> AsyncIterator[httpx.AsyncClient]:
    ip = pinned_ip or await resolve_pinned_ip(connection)
    transport = _SabSecretTransport(connection, ip, inner_transport)
    async with httpx.AsyncClient(
        timeout=SAB_TIMEOUT_SECONDS,
        follow_redirects=False,
        headers={"Accept-Encoding": "identity"},
        transport=transport,
    ) as client:
        yield client


async def _request_json(
    connection: SabConnection,
    mode: str,
    *,
    inner_transport: httpx.AsyncBaseTransport | None = None,
    pinned_ip: str | None = None,
    max_bytes: int = SAB_MAX_JSON_BYTES,
) -> object:
    try:
        async with asyncio.timeout(SAB_TIMEOUT_SECONDS):
            async with _client(
                connection, inner_transport=inner_transport, pinned_ip=pinned_ip
            ) as client:
                params = {"mode": mode, "output": "json"}
                async with client.stream(
                    "GET", f"{connection.origin}/api", params=params
                ) as response:
                    if 300 <= response.status_code < 400:
                        raise SabResponseError("sab_redirect_rejected")
                    if response.status_code in {401, 403}:
                        raise SabAuthError("sab_auth_failed")
                    if response.status_code != 200:
                        raise SabUnavailable("sab_upstream_error")
                    media_type = response.headers.get("content-type", "").split(";", 1)[0]
                    if media_type.strip().lower() != "application/json":
                        raise SabResponseError("sab_content_type_invalid")
                    encoding = response.headers.get("content-encoding", "").lower()
                    if encoding not in {"", "identity"}:
                        raise SabResponseError("sab_content_encoding_invalid")
                    chunks: list[bytes] = []
                    size = 0
                    async for chunk in response.aiter_bytes():
                        size += len(chunk)
                        if size > max_bytes:
                            raise SabResponseError("sab_response_too_large")
                        chunks.append(chunk)
        invalid_json = False
        try:
            payload = json.loads(b"".join(chunks))
        except (json.JSONDecodeError, UnicodeDecodeError):
            invalid_json = True
            payload = None
        if invalid_json:
            raise SabResponseError("sab_response_invalid")
        if isinstance(payload, dict) and payload.get("error"):
            if "api key" in str(payload["error"]).lower():
                raise SabAuthError("sab_auth_failed")
            raise SabResponseError("sab_response_error")
        return payload
    except (SabAuthError, SabResponseError, SabUnavailable):
        raise
    except (httpx.HTTPError, OSError, SsrfBlocked, TimeoutError):
        pass
    raise SabUnavailable("sab_unavailable")


async def fetch_version(
    connection: SabConnection,
    *,
    inner_transport: httpx.AsyncBaseTransport | None = None,
    pinned_ip: str | None = None,
    max_bytes: int = SAB_MAX_JSON_BYTES,
) -> str:
    payload = await _request_json(
        connection,
        "version",
        inner_transport=inner_transport,
        pinned_ip=pinned_ip,
        max_bytes=max_bytes,
    )
    if not isinstance(payload, dict):
        raise SabResponseError("sab_response_invalid")
    version = payload.get("version")
    if (
        not isinstance(version, str)
        or re.fullmatch(r"[0-9]+(?:\.[0-9]+){1,3}(?:[A-Za-z0-9._-]{0,16})?", version)
        is None
        or connection.api_key in version
    ):
        raise SabResponseError("sab_response_invalid")
    return version


async def fetch_categories(
    connection: SabConnection,
    *,
    inner_transport: httpx.AsyncBaseTransport | None = None,
    pinned_ip: str | None = None,
    max_bytes: int = SAB_MAX_JSON_BYTES,
) -> set[str]:
    payload = await _request_json(
        connection,
        "get_cats",
        inner_transport=inner_transport,
        pinned_ip=pinned_ip,
        max_bytes=max_bytes,
    )
    if not isinstance(payload, dict) or not isinstance(payload.get("categories"), list):
        raise SabResponseError("sab_response_invalid")
    categories = payload["categories"]
    if len(categories) > 100 or any(
        not isinstance(value, str) or not 1 <= len(value) <= 64 for value in categories
    ):
        raise SabResponseError("sab_response_invalid")
    return set(categories)
