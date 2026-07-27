from __future__ import annotations

from backend.models import (
    ConnectionTestResponse,
    ModuleStatus,
    SearchResponse,
    SearchResultOut,
)
from backend import routes_search
from backend.errors import IndexerUnavailable, MediacenterConfigError

BASE = "/api/modules/mediacenter"


def _search_response() -> SearchResponse:
    return SearchResponse(
        total=1,
        eligible=1,
        results=[
            SearchResultOut(
                result_id="opaque-result-id",
                title="Film.German.1080p.WEB-DL-GRP",
                media_type="movie",
                category_id=2140,
                size_bytes=1_000_000,
                age_days=1,
                decision="eligible",
                reasons=["language_confirmed", "resolution_allowed"],
                language="de",
                resolution="1080p",
                format=None,
                bitrate_kbps=None,
                score=110,
                selection_status="ready",
            )
        ],
    )


def test_all_routes_require_auth(client):
    assert client.get(f"{BASE}/status").status_code == 401
    assert client.post(f"{BASE}/connections/test").status_code == 401
    assert client.post(f"{BASE}/search", json={"query": "Film", "media_type": "movie"}).status_code == 401


def test_status_is_user_scoped(client, alice, monkeypatch):
    seen: list[str] = []

    def fake_status(username: str):
        seen.append(username)
        return ModuleStatus(
            state="ready", indexer_configured=True, sab_configured=True
        )

    monkeypatch.setattr(routes_search.service, "connection_status", fake_status)
    response = client.get(f"{BASE}/status", headers=alice)

    assert response.status_code == 200
    assert response.json() == {
        "module": "mediacenter",
        "state": "ready",
        "indexer_configured": True,
        "sab_configured": True,
        "radarr_configured": False,
        "sonarr_configured": False,
    }
    assert seen == ["alice"]


def test_connection_test_returns_sanitized_capabilities(client, alice, monkeypatch):
    async def fake_test(username: str):
        assert username == "alice"
        return ConnectionTestResponse(
            max_limit=500,
            default_limit=250,
            search_types=["book", "movie", "music", "search", "tv"],
            categories=[2140, 2145, 2150, 3010, 3040, 3130, 5140, 5145, 7120],
            sab_version="4.5.3",
            sab_categories=["audio", "audiobook", "ebook", "movies", "tv"],
        )

    monkeypatch.setattr(routes_search.service, "test_connections", fake_test)
    response = client.post(f"{BASE}/connections/test", headers=alice)

    assert response.status_code == 200
    serialized = response.text
    assert "apikey" not in serialized.lower()
    assert "tresuere_token" not in serialized
    assert "sabnzb_token" not in serialized
    assert "top-secret" not in serialized


def test_search_passes_authenticated_user_and_validated_body(client, alice, monkeypatch):
    seen = []

    async def fake_search(username, request, **kwargs):
        seen.append((username, request, kwargs.get("owner_id")))
        return _search_response()

    monkeypatch.setattr(routes_search.service, "search_indexer", fake_search)
    response = client.post(
        f"{BASE}/search",
        headers=alice,
        json={"query": "  Film   Titel  ", "media_type": "movie", "limit": 10},
    )

    assert response.status_code == 200
    assert response.json()["results"][0]["result_id"] == "opaque-result-id"
    assert seen[0][0] == "alice"
    assert seen[0][1].query == "Film Titel"
    assert seen[0][2] and seen[0][2] != "alice"


def test_search_rejects_network_and_credential_fields(client, alice):
    response = client.post(
        f"{BASE}/search",
        headers=alice,
        json={
            "query": "Film",
            "media_type": "movie",
            "url": "http://127.0.0.1/private",
            "credential": "other-secret",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "mediacenter_request_invalid"
    assert "other-secret" not in response.text
    assert "127.0.0.1" not in response.text


def test_search_rate_limit_is_per_user(client, alice, monkeypatch):
    monkeypatch.setattr(routes_search, "check_rate", lambda key, **_: (False, 17))

    response = client.post(
        f"{BASE}/search",
        headers=alice,
        json={"query": "Film", "media_type": "movie"},
    )

    assert response.status_code == 429
    assert response.json()["detail"] == {
        "code": "mediacenter_rate_limited",
        "params": {"retry_after": 17},
    }


def test_config_and_upstream_errors_are_stable(client, alice, monkeypatch):
    async def config_error(*_, **__):
        raise MediacenterConfigError("indexer_not_configured")

    monkeypatch.setattr(routes_search.service, "search_indexer", config_error)
    config_response = client.post(
        f"{BASE}/search", headers=alice, json={"query": "Film", "media_type": "movie"}
    )
    assert config_response.status_code == 503
    assert config_response.json()["detail"]["code"] == "indexer_not_configured"

    async def upstream_error(*_, **__):
        raise IndexerUnavailable("indexer_unavailable")

    monkeypatch.setattr(routes_search.service, "search_indexer", upstream_error)
    upstream_response = client.post(
        f"{BASE}/search", headers=alice, json={"query": "Film", "media_type": "movie"}
    )
    assert upstream_response.status_code == 502
    assert upstream_response.json()["detail"]["code"] == "indexer_unavailable"
