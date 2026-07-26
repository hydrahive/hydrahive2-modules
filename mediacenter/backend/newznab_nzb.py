from __future__ import annotations

import asyncio
import re

import httpx

from .config import INDEXER_TIMEOUT_SECONDS, MAX_NZB_BYTES
from .errors import IndexerResponseError, IndexerUnavailable
from .nzb_xml import validate_nzb


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
    from .newznab import _request_xml

    try:
        async with asyncio.timeout(INDEXER_TIMEOUT_SECONDS):
            data = await _request_xml(
                api_key,
                {"t": "get", "id": guid},
                inner_transport=inner_transport,
                pinned_ip=pinned_ip,
                max_bytes=max_bytes,
            )
            await asyncio.to_thread(validate_nzb, data, api_key)
            return data
    except TimeoutError:
        pass
    raise IndexerUnavailable("indexer_unavailable")
