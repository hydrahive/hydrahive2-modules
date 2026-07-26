from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from . import newznab
from .config import NEWZNAB_CATEGORIES, NEWZNAB_SEARCH_TYPES
from .credentials import resolve_indexer_api_key
from .errors import IndexerResponseError, MediacenterConfigError
from .models import (
    ConnectionTestResponse,
    ModuleStatus,
    ProfileDecision,
    SearchRequest,
    SearchResponse,
    SearchResultOut,
)
from .profiles import classify_release, set_selection_status
from .result_store import RESULTS


def connection_status(username: str) -> ModuleStatus:
    try:
        resolve_indexer_api_key(username)
    except MediacenterConfigError:
        return ModuleStatus(state="not_configured", indexer_configured=False)
    return ModuleStatus(state="ready", indexer_configured=True)


async def test_indexer_connection(username: str) -> ConnectionTestResponse:
    capabilities = await newznab.fetch_caps(resolve_indexer_api_key(username))
    required_search = set(NEWZNAB_SEARCH_TYPES.values())
    required_categories = {
        category for categories in NEWZNAB_CATEGORIES.values() for category in categories
    }
    if not required_search <= capabilities.search_types or not required_categories <= capabilities.categories:
        raise IndexerResponseError("indexer_capabilities_missing")
    return ConnectionTestResponse(
        max_limit=capabilities.max_limit,
        default_limit=capabilities.default_limit,
        search_types=sorted(capabilities.search_types),
        categories=sorted(required_categories),
    )


def _age_days(decision: ProfileDecision, now: datetime) -> int | None:
    published = decision.release.published_at
    if published is None:
        return None
    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)
    return max(0, (now - published.astimezone(timezone.utc)).days)


def _apply_filters(
    decision: ProfileDecision, request: SearchRequest, now: datetime
) -> ProfileDecision:
    reasons = list(decision.reasons)
    size = decision.release.size_bytes
    age = _age_days(decision, now)
    if request.min_size_mb is not None:
        if size is None:
            reasons.append("size_unknown")
        elif size < request.min_size_mb * 1024 * 1024:
            reasons.append("size_below_minimum")
    if request.max_size_mb is not None:
        if size is None:
            reasons.append("size_unknown")
        elif size > request.max_size_mb * 1024 * 1024:
            reasons.append("size_above_maximum")
    if request.max_age_days is not None:
        if age is None:
            reasons.append("age_unknown")
        elif age > request.max_age_days:
            reasons.append("age_above_maximum")
    filter_rejected = {
        "size_unknown", "size_below_minimum", "size_above_maximum",
        "age_unknown", "age_above_maximum",
    }
    if filter_rejected & set(reasons):
        return replace(decision, decision="rejected", reasons=tuple(dict.fromkeys(reasons)), score=0)
    return replace(decision, reasons=tuple(dict.fromkeys(reasons)))


def _result_out(
    username: str, decision: ProfileDecision, now: datetime
) -> SearchResultOut:
    result_id = RESULTS.put(username, decision) if decision.decision == "eligible" else None
    return SearchResultOut(
        result_id=result_id,
        title=decision.release.title,
        media_type=decision.media_type,
        category_id=decision.release.category_id,
        size_bytes=decision.release.size_bytes,
        age_days=_age_days(decision, now),
        decision=decision.decision,
        reasons=list(decision.reasons),
        language=decision.language,
        resolution=decision.resolution,
        format=decision.format,
        bitrate_kbps=decision.bitrate_kbps,
        score=decision.score,
        selection_status=decision.selection_status,
    )


async def search_indexer(
    username: str, request: SearchRequest, *, now: datetime | None = None
) -> SearchResponse:
    timestamp = now or datetime.now(timezone.utc)
    releases = await newznab.search(resolve_indexer_api_key(username), request)
    decisions = [
        _apply_filters(classify_release(release, request.media_type), request, timestamp)
        for release in releases
    ]
    decisions = set_selection_status(decisions, request.media_type)
    decisions.sort(key=lambda item: (item.decision != "eligible", -item.score, item.release.title.lower()))
    results = [_result_out(username, decision, timestamp) for decision in decisions]
    return SearchResponse(
        total=len(results),
        eligible=sum(result.decision == "eligible" for result in results),
        results=results,
    )
