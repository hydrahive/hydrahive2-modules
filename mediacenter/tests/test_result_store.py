from __future__ import annotations

from datetime import datetime, timezone

from backend.models import ProfileDecision, RawRelease
from backend.result_store import ResultStore


def _decision() -> ProfileDecision:
    release = RawRelease(
        title="Film.German.1080p.WEB-DL-GRP",
        guid="upstream-guid",
        category_id=2140,
        size_bytes=1_000,
        language="de",
        published_at=datetime(2026, 7, 26, tzinfo=timezone.utc),
        download_url="https://treasure-maps.com/getnzb/upstream-guid",
    )
    return ProfileDecision(
        release=release,
        media_type="movie",
        decision="eligible",
        reasons=("language_confirmed", "resolution_allowed"),
        language="de",
        resolution="1080p",
        format=None,
        bitrate_kbps=None,
        score=110,
    )


def test_result_ids_are_opaque_unique_and_owner_bound():
    store = ResultStore(ttl_seconds=900)

    first = store.put("alice", _decision(), now=100.0)
    second = store.put("alice", _decision(), now=100.0)

    assert first != second
    assert len(first) >= 22
    assert "upstream" not in first
    assert store.get("alice", first, now=101.0) is not None
    assert store.get("bob", first, now=101.0) is None


def test_result_expires_at_ttl_boundary():
    store = ResultStore(ttl_seconds=10)
    result_id = store.put("alice", _decision(), now=100.0)

    assert store.get("alice", result_id, now=109.999) is not None
    assert store.get("alice", result_id, now=110.0) is None


def test_unknown_and_manipulated_ids_return_none():
    store = ResultStore(ttl_seconds=10)
    result_id = store.put("alice", _decision(), now=100.0)

    assert store.get("alice", "unknown", now=101.0) is None
    assert store.get("alice", f"{result_id}x", now=101.0) is None


def test_store_capacity_evicts_expired_entries_before_rejecting():
    store = ResultStore(ttl_seconds=1, max_entries=2)
    old = store.put("alice", _decision(), now=100.0)
    store.put("alice", _decision(), now=100.0)

    fresh = store.put("alice", _decision(), now=102.0)

    assert store.get("alice", old, now=102.0) is None
    assert store.get("alice", fresh, now=102.0) is not None
