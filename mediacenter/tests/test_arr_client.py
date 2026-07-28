"""arr_client.push_release — nutzt den zustandslosen /release/push-Endpunkt (Fix)."""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from backend import arr_client


class _Conn:
    service = "radarr"
    origin = "http://arr.example:7878"
    api_key = "geheim"


def _release(**over):
    base = dict(
        title="Test.Movie.2020.1080p.WEB-DL",
        guid="hydrahive-guid-1",
        category_id=2000,
        size_bytes=1_048_576,
        language="de",
        published_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
        download_url="http://indexer/dl/abc.nzb",
        meta=None,
    )
    base.update(over)
    return SimpleNamespace(**base)


@pytest.mark.asyncio
async def test_push_release_uses_push_endpoint(monkeypatch):
    calls = []

    async def fake_request(connection, method, path, *, params=None, json_body=None):
        calls.append((method, path, json_body))
        return [{"guid": "PUSH-x"}]

    monkeypatch.setattr(arr_client, "_request", fake_request)
    ok = await arr_client.push_release(_Conn(), _release(), indexer_id=2)
    assert ok is True
    assert len(calls) == 1
    method, path, body = calls[0]
    assert method == "POST"
    # DER KERN DES FIX: /release/push statt /release (cache-basiert)
    assert path == "/api/v3/release/push"
    # vollstaendiges ReleaseResource statt nur {guid, indexerId}
    assert body["guid"] == "hydrahive-guid-1"
    assert body["title"] == "Test.Movie.2020.1080p.WEB-DL"
    assert body["downloadUrl"] == "http://indexer/dl/abc.nzb"
    assert body["protocol"] == "usenet"
    assert body["indexerId"] == 2
    assert body["size"] == 1_048_576
    assert body["publishDate"] == "2020-01-01T00:00:00Z"


@pytest.mark.asyncio
async def test_push_release_publishdate_fallback(monkeypatch):
    """Ohne published_at wird ein gueltiges publishDate erzeugt (Pflichtfeld)."""
    captured = {}

    async def fake_request(connection, method, path, *, params=None, json_body=None):
        captured.update(json_body)
        return []

    monkeypatch.setattr(arr_client, "_request", fake_request)
    await arr_client.push_release(_Conn(), _release(published_at=None), indexer_id=3)
    assert captured["publishDate"].endswith("Z")
    assert len(captured["publishDate"]) == 20  # ISO 8601 …Z


@pytest.mark.asyncio
async def test_push_release_handles_missing_url_and_size(monkeypatch):
    captured = {}

    async def fake_request(connection, method, path, *, params=None, json_body=None):
        captured.update(json_body)
        return []

    monkeypatch.setattr(arr_client, "_request", fake_request)
    await arr_client.push_release(
        _Conn(), _release(download_url=None, size_bytes=None), indexer_id=2
    )
    assert captured["downloadUrl"] == ""
    assert captured["size"] == 0
