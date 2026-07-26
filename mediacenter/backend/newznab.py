from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx

from hydrahive.net.ssrf import pin_request, resolve_validated_ip

from .config import (
    INDEXER_API_URL,
    INDEXER_TIMEOUT_SECONDS,
    MAX_XML_BYTES,
    NEWZNAB_CATEGORIES,
    NEWZNAB_SEARCH_TYPES,
)
from .errors import IndexerAuthError, IndexerResponseError, IndexerUnavailable
from .models import IndexerCapabilities, RawRelease, SearchRequest
from .newznab_xml import parse_caps, parse_search

_XML_TYPES = ("text/xml", "application/xml", "application/rss+xml")


class _SecretQueryTransport(httpx.AsyncBaseTransport):
    """Injiziert den API-Key nur in eine Wire-Kopie der geloggten Request."""

    def __init__(
        self,
        api_key: str,
        pinned_ip: str,
        inner: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._pinned_ip = pinned_ip
        self._inner = inner or httpx.AsyncHTTPTransport()

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if (
            request.url.scheme != "https"
            or request.url.host != "treasure-maps.com"
            or request.url.port not in {None, 443}
            or request.url.path != "/api"
        ):
            raise IndexerResponseError("indexer_origin_rejected")
        wire = httpx.Request(
            method=request.method,
            url=request.url.copy_merge_params({"apikey": self._api_key}),
            headers=request.headers,
            stream=request.stream,
            extensions=dict(request.extensions),
        )
        pin_request(wire, {"treasure-maps.com": self._pinned_ip})
        return await self._inner.handle_async_request(wire)

    async def aclose(self) -> None:
        await self._inner.aclose()


@asynccontextmanager
async def _client(
    api_key: str,
    *,
    inner_transport: httpx.AsyncBaseTransport | None = None,
    pinned_ip: str | None = None,
) -> AsyncIterator[httpx.AsyncClient]:
    ip = pinned_ip or resolve_validated_ip("treasure-maps.com")
    transport = _SecretQueryTransport(api_key, ip, inner_transport)
    async with httpx.AsyncClient(
        timeout=INDEXER_TIMEOUT_SECONDS,
        follow_redirects=False,
        transport=transport,
    ) as client:
        yield client


async def _request_xml(
    api_key: str,
    params: dict[str, str],
    *,
    inner_transport: httpx.AsyncBaseTransport | None = None,
    pinned_ip: str | None = None,
    max_bytes: int = MAX_XML_BYTES,
) -> bytes:
    try:
        async with _client(
            api_key, inner_transport=inner_transport, pinned_ip=pinned_ip
        ) as client:
            async with client.stream("GET", INDEXER_API_URL, params=params) as response:
                if 300 <= response.status_code < 400:
                    raise IndexerResponseError("indexer_redirect_rejected")
                if response.status_code in {401, 403}:
                    raise IndexerAuthError("indexer_auth_failed")
                if response.status_code != 200:
                    raise IndexerUnavailable("indexer_upstream_error")
                content_type = response.headers.get("content-type", "").lower()
                if not any(kind in content_type for kind in _XML_TYPES):
                    raise IndexerResponseError("indexer_content_type_invalid")
                chunks: list[bytes] = []
                size = 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > max_bytes:
                        raise IndexerResponseError("indexer_response_too_large")
                    chunks.append(chunk)
                return b"".join(chunks)
    except (IndexerAuthError, IndexerResponseError, IndexerUnavailable):
        raise
    except httpx.HTTPError as exc:
        raise IndexerUnavailable("indexer_unavailable") from exc
    except OSError as exc:
        raise IndexerUnavailable("indexer_unavailable") from exc


async def fetch_caps(
    api_key: str,
    *,
    inner_transport: httpx.AsyncBaseTransport | None = None,
    pinned_ip: str | None = None,
    max_bytes: int = MAX_XML_BYTES,
) -> IndexerCapabilities:
    data = await _request_xml(
        api_key,
        {"t": "caps"},
        inner_transport=inner_transport,
        pinned_ip=pinned_ip,
        max_bytes=max_bytes,
    )
    return parse_caps(data)


def build_search_params(request: SearchRequest) -> dict[str, str]:
    params = {
        "t": NEWZNAB_SEARCH_TYPES[request.media_type],
        "q": request.query,
        "cat": ",".join(str(value) for value in NEWZNAB_CATEGORIES[request.media_type]),
        "limit": str(request.limit),
    }
    if request.year is not None:
        params["year"] = str(request.year)
    if request.media_type == "tv":
        if request.season is not None:
            params["season"] = str(request.season)
        if request.episode is not None:
            params["ep"] = request.episode
    if request.media_type == "book" and request.author is not None:
        params["author"] = request.author
    if request.media_type == "music" and request.artist is not None:
        params["artist"] = request.artist
    if request.max_age_days is not None:
        params["maxage"] = str(request.max_age_days)
    return params


async def search(
    api_key: str,
    request: SearchRequest,
    *,
    inner_transport: httpx.AsyncBaseTransport | None = None,
    pinned_ip: str | None = None,
) -> list[RawRelease]:
    data = await _request_xml(
        api_key,
        build_search_params(request),
        inner_transport=inner_transport,
        pinned_ip=pinned_ip,
    )
    return parse_search(data, max_items=request.limit)
