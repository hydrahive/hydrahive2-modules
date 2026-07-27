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


# --- Regression: Metadaten muessen den Result-Store ueberleben -------------

def test_metadaten_ueberleben_das_speichern():
    """BUG (till, 27.07.): "An Radarr uebergeben" meldete
    "Dem Treffer fehlt eine IMDb-/TVDB-Kennung".

    Ursache: _StoredRawRelease kannte kein `meta`-Feld. Beim Serialisieren
    fielen Cover, IMDb-/TVDB-Kennung und Handlung still weg — die Uebergabe
    konnte den Titel danach nicht mehr zuordnen.
    """
    from datetime import datetime, timezone

    from backend.models import ProfileDecision, RawRelease, ReleaseMeta
    from backend.result_codec import deserialize_profile_decision, serialize_profile_decision

    meta = ReleaseMeta(
        imdb_id="0133093", tmdb_id="603", tvdb_id="121361",
        cover_url="https://picbit.io/x-cover.webp",
        backdrop_url="https://picbit.io/x-backdrop.webp",
        title_clean="The Matrix", year=1999, score=8.7,
        genres=("Action", "Science Fiction"), plot="Ein Hacker …",
        season=2, episode=5, artist="A", album="B", label="C",
    )
    release = RawRelease(
        title="Matrix.1999.German.1080p", guid="g1", category_id=2140,
        size_bytes=1000, language="de",
        published_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
        download_url="https://treasure-maps.com/getnzb/g1", meta=meta,
    )
    decision = ProfileDecision(
        release, "movie", "eligible", ("language_confirmed",),
        "de", "1080", None, None, 10,
    )

    restored = deserialize_profile_decision(serialize_profile_decision(decision))

    assert restored.release.meta is not None, "meta darf nicht verloren gehen"
    assert restored.release.meta.imdb_id == "0133093"
    assert restored.release.meta.tvdb_id == "121361"
    assert restored.release.meta.cover_url == "https://picbit.io/x-cover.webp"
    assert restored.release.meta.title_clean == "The Matrix"
    assert restored.release.meta.year == 1999
    assert restored.release.meta.score == 8.7
    assert list(restored.release.meta.genres) == ["Action", "Science Fiction"]
    assert restored.release.meta.season == 2


def test_treffer_ohne_metadaten_bleibt_speicherbar():
    """Rueckwaertskompatibel: aeltere Treffer haben kein meta."""
    from datetime import datetime, timezone

    from backend.models import ProfileDecision, RawRelease
    from backend.result_codec import deserialize_profile_decision, serialize_profile_decision

    release = RawRelease(
        title="Alt.Release", guid="g2", category_id=2140, size_bytes=1,
        language="de", published_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
        download_url=None, meta=None,
    )
    decision = ProfileDecision(release, "movie", "eligible", (), "de", None, None, None, 1)

    assert deserialize_profile_decision(serialize_profile_decision(decision)).release.meta is None


def test_fremde_cover_url_wird_beim_laden_verworfen():
    """Der Store ist eine Vertrauensgrenze: eine manipulierte Ablage darf
    keine beliebige Bild-URL ins Frontend schmuggeln."""
    import json

    from backend.result_codec import deserialize_profile_decision

    payload = json.loads(_MINIMAL_PAYLOAD)
    payload["release"]["meta"] = {"cover_url": "https://evil.example/x.webp",
                                  "imdb_id": "0133093"}
    restored = deserialize_profile_decision(json.dumps(payload))
    assert restored.release.meta.cover_url is None
    assert restored.release.meta.imdb_id == "0133093"


_MINIMAL_PAYLOAD = """{
  "release": {"title": "T", "guid": "g", "category_id": 2140, "size_bytes": 1,
              "language": "de", "published_at": null, "download_url": null},
  "media_type": "movie", "decision": "eligible", "reasons": [],
  "language": "de", "resolution": null, "format": null, "bitrate_kbps": null,
  "score": 1, "selection_status": "ready"
}"""
