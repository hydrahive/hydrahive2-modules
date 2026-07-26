from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from backend.models import ProfileDecision, RawRelease
from backend.result_store import ResultStore
from backend.result_store_sqlite import SQLiteResultStore
from hydrahive.db.connection import db


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


def test_per_user_capacity_cannot_evict_another_users_results():
    store = ResultStore(ttl_seconds=60, max_entries=2)
    alice_first = store.put("alice", _decision(), now=100)
    alice_second = store.put("alice", _decision(), now=101)

    store.put("bob", _decision(), now=102)
    store.put("bob", _decision(), now=103)
    store.put("bob", _decision(), now=104)

    assert store.get("alice", alice_first, now=105) is not None
    assert store.get("alice", alice_second, now=105) is not None


def test_claim_is_atomic_and_can_be_released_only_with_claim_token():
    store = ResultStore(ttl_seconds=60)
    result_id = store.put("alice", _decision(), now=100)

    claimed = store.claim("alice", result_id, now=101)

    assert claimed is not None
    assert claimed.claim_id
    assert store.claim("alice", result_id, now=102) is None
    assert store.release("alice", result_id, "wrong-token", now=103) is False
    assert store.release("alice", result_id, claimed.claim_id, now=104) is True
    assert store.claim("alice", result_id, now=105) is not None


def test_claim_extends_lease_and_is_not_evicted_by_new_results():
    store = ResultStore(ttl_seconds=10, max_entries=2)
    claimed_id = store.put("alice", _decision(), now=100)
    other_id = store.put("alice", _decision(), now=101)
    claimed = store.claim("alice", claimed_id, now=109)
    assert claimed is not None

    store.put("alice", _decision(), now=110)

    assert store.get("alice", claimed_id, now=115) is not None
    assert store.get("alice", other_id, now=115) is None


def test_custom_claim_lease_can_be_renewed_and_expires_independently():
    store = ResultStore(ttl_seconds=100, claim_ttl_seconds=5)
    result_id = store.put("alice", _decision(), now=100)
    claimed = store.claim("alice", result_id, now=101)
    assert claimed is not None and claimed.claim_id is not None

    assert store.renew("alice", result_id, claimed.claim_id, now=104) is True
    assert store.get("alice", result_id, now=108).claim_id == claimed.claim_id
    available = store.get("alice", result_id, now=109)
    assert available is not None and available.claim_id is None
    assert available.expires_at == 200


def test_release_after_original_result_ttl_does_not_revive_result():
    store = ResultStore(ttl_seconds=10)
    result_id = store.put("alice", _decision(), now=100)
    claimed = store.claim("alice", result_id, now=109)
    assert claimed is not None and claimed.claim_id is not None

    assert store.release("alice", result_id, claimed.claim_id, now=115) is True
    assert store.get("alice", result_id, now=115) is None


def test_parallel_claim_allows_exactly_one_winner():
    store = ResultStore(ttl_seconds=60)
    result_id = store.put("alice", _decision(), now=100)

    with ThreadPoolExecutor(max_workers=8) as executor:
        claims = list(
            executor.map(
                lambda _: store.claim("alice", result_id, now=101),
                range(16),
            )
        )

    assert sum(claim is not None for claim in claims) == 1


def test_consume_is_owner_and_claim_token_bound_and_removes_result():
    store = ResultStore(ttl_seconds=60)
    result_id = store.put("alice", _decision(), now=100)
    claimed = store.claim("alice", result_id, now=101)
    assert claimed is not None and claimed.claim_id is not None

    assert store.consume("bob", result_id, claimed.claim_id, now=102) is None
    assert store.consume("alice", result_id, "wrong", now=102) is None
    assert store.consume("alice", result_id, claimed.claim_id, now=102) is not None
    assert store.get("alice", result_id, now=103) is None


def test_store_capacity_evicts_expired_entries_before_rejecting():
    store = ResultStore(ttl_seconds=1, max_entries=2)
    old = store.put("alice", _decision(), now=100.0)
    store.put("alice", _decision(), now=100.0)

    fresh = store.put("alice", _decision(), now=102.0)

    assert store.get("alice", old, now=102.0) is None
    assert store.get("alice", fresh, now=102.0) is not None


def test_sqlite_result_is_shared_between_store_instances():
    instance_a = SQLiteResultStore(ttl_seconds=60)
    instance_b = SQLiteResultStore(ttl_seconds=60)

    result_id = instance_a.put("alice", _decision(), now=100)
    persisted = instance_b.get("alice", result_id, now=101)
    claimed = instance_b.claim("alice", result_id, now=102)

    assert persisted is not None
    assert persisted.decision == _decision()
    assert claimed is not None and claimed.claim_id is not None
    assert instance_a.get("alice", result_id, now=103).claim_id == claimed.claim_id


def test_sqlite_capacity_is_owner_bound_and_cleans_expired_entries():
    store = SQLiteResultStore(ttl_seconds=10, max_entries=2)
    alice_first = store.put("alice", _decision(), now=100)
    alice_second = store.put("alice", _decision(), now=101)
    store.put("bob", _decision(), now=101)
    store.put("bob", _decision(), now=102)
    store.put("bob", _decision(), now=103)

    assert store.get("alice", alice_first, now=101.5) is not None
    assert store.get("alice", alice_second, now=101.5) is not None

    fresh = store.put("alice", _decision(), now=112)
    assert store.get("alice", alice_first, now=112) is None
    assert store.get("alice", fresh, now=112) is not None


def test_sqlite_corrupt_payload_is_rejected_and_deleted():
    store = SQLiteResultStore(ttl_seconds=60)
    result_id = store.put("alice", _decision(), now=100)
    with db() as conn:
        conn.execute(
            "UPDATE module_mediacenter_results SET payload_json = ? WHERE result_id = ?",
            ('{"release":{"download_url":"http://127.0.0.1/private"}}', result_id),
        )
        conn.commit()

    assert store.get("alice", result_id, now=101) is None
    with db() as conn:
        row = conn.execute(
            "SELECT 1 FROM module_mediacenter_results WHERE result_id = ?",
            (result_id,),
        ).fetchone()
    assert row is None


def test_sqlite_parallel_claim_allows_exactly_one_winner():
    instance_a = SQLiteResultStore(ttl_seconds=60)
    instance_b = SQLiteResultStore(ttl_seconds=60)
    result_id = instance_a.put("alice", _decision(), now=100)

    with ThreadPoolExecutor(max_workers=8) as executor:
        claims = list(
            executor.map(
                lambda index: (instance_a if index % 2 else instance_b).claim(
                    "alice", result_id, now=101
                ),
                range(16),
            )
        )

    assert sum(claim is not None for claim in claims) == 1
