from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend import service
from backend.errors import IndexerResponseError
from backend.models import IndexerCapabilities, RawRelease, SearchRequest


def _release(title: str, guid: str, *, category: int = 2140, size_mb: int = 1000, days_old: int = 1):
    return RawRelease(
        title=title,
        guid=guid,
        category_id=category,
        size_bytes=size_mb * 1024 * 1024,
        language=None,
        published_at=datetime(2026, 7, 26, tzinfo=timezone.utc) - timedelta(days=days_old),
        download_url=f"https://treasure-maps.com/getnzb/{guid}",
    )


async def test_search_classifies_sorts_and_stores_only_eligible_results(monkeypatch):
    releases = [
        _release("Film.MULTI.2160p.WEB-DL-GRP", "bad-language", category=9999),
        _release("Film.German.1080p.WEB-DL-GRP", "good-1080"),
    ]
    monkeypatch.setattr(service, "resolve_indexer_api_key", lambda username: "secret")
    monkeypatch.setattr(service.newznab, "search", lambda *_: _async_result(releases))

    response = await service.search_indexer(
        "alice",
        SearchRequest(query="Film", media_type="movie"),
        now=datetime(2026, 7, 26, tzinfo=timezone.utc),
    )

    assert response.total == 2
    assert response.eligible == 1
    assert response.results[0].decision == "eligible"
    assert response.results[0].result_id
    assert response.results[1].decision == "rejected"
    assert response.results[1].result_id is None
    serialized = response.model_dump_json()
    assert "getnzb" not in serialized
    assert "bad-language" not in serialized
    assert "secret" not in serialized


async def test_search_enforces_size_and_age_filters(monkeypatch):
    releases = [
        _release("Film.German.1080p.WEB-DL-GRP", "small", size_mb=100, days_old=1),
        _release("Film.German.1080p.WEB-DL-GRP", "old", size_mb=2000, days_old=90),
        _release("Film.German.1080p.WEB-DL-GRP", "good", size_mb=2000, days_old=1),
    ]
    monkeypatch.setattr(service, "resolve_indexer_api_key", lambda username: "secret")
    monkeypatch.setattr(service.newznab, "search", lambda *_: _async_result(releases))

    response = await service.search_indexer(
        "alice",
        SearchRequest(
            query="Film", media_type="movie", min_size_mb=1000, max_age_days=30
        ),
        now=datetime(2026, 7, 26, tzinfo=timezone.utc),
    )

    all_reasons = [set(result.reasons) for result in response.results]
    assert any("size_below_minimum" in reasons for reasons in all_reasons)
    assert any("age_above_maximum" in reasons for reasons in all_reasons)
    assert response.eligible == 1


async def test_search_marks_quality_preference_across_eligible_results(monkeypatch):
    releases = [
        _release("Film.German.1080p.WEB-DL-GRP", "low"),
        _release("Film.German.2160p.WEB-DL-GRP", "high"),
    ]
    monkeypatch.setattr(service, "resolve_indexer_api_key", lambda username: "secret")
    monkeypatch.setattr(service.newznab, "search", lambda *_: _async_result(releases))

    response = await service.search_indexer("alice", SearchRequest(query="Film", media_type="movie"))

    assert {item.selection_status for item in response.results} == {"quality_preference_required"}


async def test_connection_test_requires_all_v1_capabilities(monkeypatch):
    monkeypatch.setattr(service, "resolve_indexer_api_key", lambda username: "secret")
    incomplete = IndexerCapabilities(
        max_limit=500,
        default_limit=250,
        search_types={"search", "movie"},
        categories={2140},
    )
    monkeypatch.setattr(service.newznab, "fetch_caps", lambda *_: _async_result(incomplete))

    with pytest.raises(IndexerResponseError) as exc_info:
        await service.test_indexer_connection("alice")

    assert exc_info.value.code == "indexer_capabilities_missing"


async def _async_result(value):
    return value
