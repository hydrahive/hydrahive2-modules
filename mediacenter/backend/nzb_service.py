from __future__ import annotations

from . import newznab
from .credentials import resolve_indexer_api_key
from .errors import IndexerResponseError
from .result_registry import RESULTS


async def download_result_nzb(
    username: str, result_id: str, *, now: float | None = None
) -> bytes:
    stored = RESULTS.get(username, result_id, now=now)
    if stored is None or stored.decision.decision != "eligible":
        raise IndexerResponseError("result_unavailable")
    return await newznab.fetch_nzb(
        resolve_indexer_api_key(username), stored.decision.release.guid
    )
