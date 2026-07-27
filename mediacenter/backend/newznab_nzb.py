from __future__ import annotations

import asyncio
import re
from urllib.parse import quote

import httpx

from hydrahive.net.ssrf import SsrfBlocked, pin_request, resolve_validated_ip

from .config import INDEXER_FILE_HOST, INDEXER_TIMEOUT_SECONDS, MAX_NZB_BYTES
from .errors import (
    IndexerAuthError,
    IndexerResponseError,
    IndexerUnavailable,
)
from .nzb_xml import validate_nzb


_NZB_TYPES = ("application/x-nzb", "application/xml", "text/xml")


class _FileTransport(httpx.AsyncBaseTransport):
    """Injiziert das geheime `r` nur in die gepinnte Wire-Request."""

    def __init__(
        self, api_key: str, pinned_ip: str, expected_path: str,
        inner: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._pinned_ip = pinned_ip
        self._expected_path = expected_path
        self._inner = inner or httpx.AsyncHTTPTransport()

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if (
            request.url.scheme != "https"
            or request.url.host != INDEXER_FILE_HOST
            or request.url.port not in {None, 443}
            or request.url.raw_path != self._expected_path.encode("ascii")
            or request.url.query
        ):
            raise IndexerResponseError("indexer_origin_rejected")
        wire = httpx.Request(
            method=request.method,
            url=request.url.copy_merge_params({"r": self._api_key}),
            headers=request.headers,
            stream=request.stream,
            extensions=dict(request.extensions),
        )
        pin_request(wire, {INDEXER_FILE_HOST: self._pinned_ip})
        return await self._inner.handle_async_request(wire)

    async def aclose(self) -> None:
        await self._inner.aclose()


async def fetch_nzb(
    api_key: str,
    guid: str,
    *,
    inner_transport: httpx.AsyncBaseTransport | None = None,
    pinned_ip: str | None = None,
    max_bytes: int = MAX_NZB_BYTES,
) -> bytes:
    if (
        not 1 <= len(guid) <= 512
        or re.search(r"[\x00-\x20\x7f]", guid)
        or api_key in guid
    ):
        raise IndexerResponseError("indexer_identifier_invalid")
    path = f"/getnzb/{quote(guid, safe='')}"
    try:
        async with asyncio.timeout(INDEXER_TIMEOUT_SECONDS):
            ip = pinned_ip or await asyncio.to_thread(resolve_validated_ip, INDEXER_FILE_HOST)
            transport = _FileTransport(api_key, ip, path, inner_transport)
            async with httpx.AsyncClient(
                timeout=INDEXER_TIMEOUT_SECONDS,
                follow_redirects=False,
                headers={"Accept-Encoding": "identity"},
                transport=transport,
            ) as client:
                async with client.stream("GET", f"https://{INDEXER_FILE_HOST}{path}") as response:
                    if 300 <= response.status_code < 400:
                        raise IndexerResponseError("indexer_redirect_rejected")
                    if response.status_code in {401, 403}:
                        raise IndexerAuthError("indexer_auth_failed")
                    if response.status_code != 200:
                        raise IndexerUnavailable("indexer_upstream_error")
                    content_type = response.headers.get("content-type", "").lower()
                    if not any(kind in content_type for kind in _NZB_TYPES):
                        raise IndexerResponseError("indexer_content_type_invalid")
                    encoding = response.headers.get("content-encoding", "").lower()
                    if encoding not in {"", "identity"}:
                        raise IndexerResponseError("indexer_content_encoding_invalid")
                    chunks: list[bytes] = []
                    size = 0
                    async for chunk in response.aiter_bytes():
                        size += len(chunk)
                        if size > max_bytes:
                            raise IndexerResponseError("indexer_response_too_large")
                        chunks.append(chunk)
            data = b"".join(chunks)
            await asyncio.to_thread(validate_nzb, data, api_key)
            return data
    except (IndexerAuthError, IndexerResponseError, IndexerUnavailable):
        raise
    except (httpx.HTTPError, OSError, SsrfBlocked, TimeoutError):
        pass
    raise IndexerUnavailable("indexer_unavailable")
