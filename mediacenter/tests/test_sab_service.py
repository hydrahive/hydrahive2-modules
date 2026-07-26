from __future__ import annotations

import pytest

from backend import service
from backend.config import SAB_CATEGORIES
from backend.errors import SabResponseError
from backend.models import ConnectionTestResponse, IndexerCapabilities
from backend.sab_credentials import SabConnection


async def _value(value):
    return value


@pytest.mark.parametrize(
    "media_type,category",
    [
        ("movie", "movies"),
        ("tv", "tv"),
        ("book", "ebook"),
        ("audiobook", "audiobook"),
        ("audioplay", "audiobook"),
        ("music", "audio"),
    ],
)
def test_sab_category_mapping_is_fixed_per_media_type(media_type, category):
    assert SAB_CATEGORIES[media_type] == category


async def test_combined_connection_test_requires_sab_categories(monkeypatch):
    capabilities = IndexerCapabilities(
        max_limit=500,
        default_limit=250,
        search_types={"search", "movie", "tv", "book", "music"},
        categories={2140, 2145, 2150, 3010, 3040, 3130, 5140, 5145, 7120},
    )
    monkeypatch.setattr(service, "resolve_indexer_api_key", lambda _: "indexer-key")
    monkeypatch.setattr(
        service,
        "resolve_sab_connection",
        lambda _: SabConnection("http://sab.example:8080", "sab-key"),
    )
    monkeypatch.setattr(service.newznab, "fetch_caps", lambda *_: _value(capabilities))
    monkeypatch.setattr(
        service.sabnzbd, "resolve_pinned_ip", lambda *_: _value("93.184.216.34")
    )
    monkeypatch.setattr(
        service.sabnzbd, "fetch_version", lambda *_, **__: _value("4.5.3")
    )
    monkeypatch.setattr(
        service.sabnzbd,
        "fetch_categories",
        lambda *_, **__: _value({"movies", "tv", "audio", "audiobook", "ebook"}),
    )

    response = await service.test_connections("alice")

    assert isinstance(response, ConnectionTestResponse)
    assert response.ok is True
    assert response.sab_version == "4.5.3"
    assert response.sab_categories == ["audio", "audiobook", "ebook", "movies", "tv"]


async def test_combined_connection_test_rejects_missing_sab_category(monkeypatch):
    monkeypatch.setattr(
        service, "test_indexer_connection", lambda *_: _value(ConnectionTestResponse(
            max_limit=500,
            default_limit=250,
            search_types=["book", "movie", "music", "search", "tv"],
            categories=[2140, 2145, 2150, 3010, 3040, 3130, 5140, 5145, 7120],
        ))
    )
    monkeypatch.setattr(
        service,
        "resolve_sab_connection",
        lambda _: SabConnection("http://sab.example:8080", "sab-key"),
    )
    monkeypatch.setattr(
        service.sabnzbd, "resolve_pinned_ip", lambda *_: _value("93.184.216.34")
    )
    monkeypatch.setattr(
        service.sabnzbd, "fetch_version", lambda *_, **__: _value("4.5.3")
    )
    monkeypatch.setattr(
        service.sabnzbd,
        "fetch_categories",
        lambda *_, **__: _value({"movies", "tv", "audio", "ebook"}),
    )

    with pytest.raises(SabResponseError) as exc_info:
        await service.test_connections("alice")

    assert exc_info.value.code == "sab_categories_missing"


def test_connection_status_requires_both_user_scoped_credentials(monkeypatch):
    monkeypatch.setattr(service, "resolve_indexer_api_key", lambda _: "indexer-key")
    monkeypatch.setattr(
        service,
        "resolve_sab_connection",
        lambda _: SabConnection("http://sab.example:8080", "sab-key"),
    )

    status = service.connection_status("alice")

    assert status.state == "ready"
    assert status.indexer_configured is True
    assert status.sab_configured is True
