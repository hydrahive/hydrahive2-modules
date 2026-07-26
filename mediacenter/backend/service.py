from __future__ import annotations

import re
from dataclasses import replace
from datetime import datetime, timezone

from . import newznab, sabnzbd
from .config import NEWZNAB_CATEGORIES, SAB_CATEGORIES
from .credentials import resolve_indexer_api_key
from .errors import IndexerResponseError, MediacenterConfigError, SabResponseError
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
from .sab_credentials import resolve_sab_connection


def connection_status(username: str) -> ModuleStatus:
    try:
        resolve_indexer_api_key(username)
        indexer_configured = True
    except MediacenterConfigError:
        indexer_configured = False
    try:
        resolve_sab_connection(username)
        sab_configured = True
    except MediacenterConfigError:
        sab_configured = False
    state = "ready" if indexer_configured and sab_configured else "not_configured"
    return ModuleStatus(
        state=state,
        indexer_configured=indexer_configured,
        sab_configured=sab_configured,
    )


async def test_indexer_connection(username: str) -> ConnectionTestResponse:
    capabilities = await newznab.fetch_caps(resolve_indexer_api_key(username))
    required_search = {"search", "movie", "tv", "music", "book"}
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


async def test_connections(username: str) -> ConnectionTestResponse:
    indexer = await test_indexer_connection(username)
    connection = resolve_sab_connection(username)
    pinned_ip = await sabnzbd.resolve_pinned_ip(connection)
    version = await sabnzbd.fetch_version(connection, pinned_ip=pinned_ip)
    categories = await sabnzbd.fetch_categories(connection, pinned_ip=pinned_ip)
    required = set(SAB_CATEGORIES.values())
    if not required <= categories:
        raise SabResponseError("sab_categories_missing")
    return indexer.model_copy(
        update={
            "sab_version": version,
            "sab_categories": sorted(required),
        }
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


def _title_contains(title_tokens: set[str], value: str | None) -> bool:
    if not value:
        return False
    expected = set(re.findall(r"[A-Z0-9]+", value.upper()))
    return bool(expected) and expected <= title_tokens


def _rank_request_match(
    decision: ProfileDecision, request: SearchRequest
) -> ProfileDecision:
    if decision.decision != "eligible" or request.media_type != "music":
        return decision
    title_tokens = set(re.findall(r"[A-Z0-9]+", decision.release.title.upper()))
    reasons = list(decision.reasons)
    bonus = 0
    if _title_contains(title_tokens, request.artist):
        reasons.append("requested_artist_match")
        bonus += 15
    if _title_contains(title_tokens, request.album):
        incomplete = {"SINGLE", "CDS", "INCOMPLETE", "PARTIAL", "TRACK", "PREVIEW"}
        track_number = re.search(
            r"(?:^|[._ -])(?:TRACK[._ -]?)?0?[1-9](?:[._ -]|$)",
            decision.release.title.upper(),
        )
        if title_tokens.isdisjoint(incomplete) and track_number is None:
            reasons.append("requested_album_complete")
            bonus += 30
        else:
            reasons.append("requested_album_incomplete")
    if request.year is not None and str(request.year) in title_tokens:
        reasons.append("requested_year_match")
        bonus += 5
    return replace(decision, reasons=tuple(reasons), score=decision.score + bonus)


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
    decisions = []
    allowed_categories = set(NEWZNAB_CATEGORIES[request.media_type])
    for release in releases:
        decision = _rank_request_match(
            classify_release(release, request.media_type), request
        )
        if release.category_id not in allowed_categories:
            decision = replace(
                decision,
                decision="rejected",
                reasons=("category_mismatch",),
                score=0,
            )
        decisions.append(_apply_filters(decision, request, timestamp))
    decisions = set_selection_status(decisions, request.media_type)
    decisions.sort(key=lambda item: (item.decision != "eligible", -item.score, item.release.title.lower()))
    results = [_result_out(username, decision, timestamp) for decision in decisions]
    return SearchResponse(
        total=len(results),
        eligible=sum(result.decision == "eligible" for result in results),
        results=results,
    )
