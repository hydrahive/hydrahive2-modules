from __future__ import annotations

import httpx
import pytest

from backend import newznab, nzb_service
from backend.errors import IndexerResponseError
from backend.models import ProfileDecision, RawRelease
from backend.result_store import ResultStore

_NZB = b'''<?xml version="1.0"?><nzb xmlns="http://www.newzbin.com/DTD/2003/nzb"><file poster="x" date="1" subject="safe"><groups><group>a</group></groups><segments><segment bytes="1" number="1">id</segment></segments></file></nzb>'''


async def test_fetch_nzb_reconstructs_fixed_newznab_request_from_identifier():
    captured = []

    async def handler(request: httpx.Request):
        captured.append(request)
        return httpx.Response(200, headers={"content-type": "application/x-nzb"}, content=_NZB)

    data = await newznab.fetch_nzb(
        "secret", "safe-guid-123", inner_transport=httpx.MockTransport(handler),
        pinned_ip="93.184.216.34",
    )

    assert data == _NZB
    assert captured[0].url.params["t"] == "get"
    assert captured[0].url.params["id"] == "safe-guid-123"
    assert captured[0].url.host == "93.184.216.34"


@pytest.mark.parametrize(
    "body,code",
    [
        (b'<!DOCTYPE nzb [<!ENTITY x "boom">]><nzb>&x;</nzb>', "indexer_xml_unsafe"),
        (b"<rss />", "indexer_nzb_invalid"),
        (b"<nzb>", "indexer_xml_invalid"),
    ],
)
async def test_fetch_nzb_rejects_unsafe_or_invalid_xml(body, code):
    transport = httpx.MockTransport(
        lambda _: httpx.Response(200, headers={"content-type": "application/x-nzb"}, content=body)
    )
    with pytest.raises(IndexerResponseError) as exc_info:
        await newznab.fetch_nzb(
            "secret", "safe-guid", inner_transport=transport, pinned_ip="93.184.216.34"
        )
    assert exc_info.value.code == code


@pytest.mark.parametrize("encoding", ["plain", "url", "xml_entity", "comment"])
async def test_fetch_nzb_rejects_api_key_reflection(encoding):
    secret = "never-return-this-key"
    reflected = secret
    if encoding == "url":
        reflected = secret.replace("-", "%252D")
    elif encoding == "xml_entity":
        reflected = "".join(f"&#{ord(char)};" for char in secret)
    if encoding == "comment":
        body = _NZB.replace(b"<file ", f"<!--{secret}--><file ".encode())
    else:
        body = _NZB.replace(b'poster="x"', f'poster="{reflected}"'.encode())
    transport = httpx.MockTransport(
        lambda _: httpx.Response(200, headers={"content-type": "application/x-nzb"}, content=body)
    )
    with pytest.raises(IndexerResponseError) as exc_info:
        await newznab.fetch_nzb(
            secret, "safe", inner_transport=transport, pinned_ip="93.184.216.34"
        )
    assert exc_info.value.code == "indexer_nzb_secret_reflected"


async def test_fetch_nzb_rejects_utf16_dtd():
    body = '<?xml version="1.0" encoding="UTF-16"?><!DOCTYPE nzb [<!ENTITY x "boom">]><nzb><file poster="&x;" /></nzb>'.encode("utf-16")
    transport = httpx.MockTransport(
        lambda _: httpx.Response(200, headers={"content-type": "application/x-nzb"}, content=body)
    )
    with pytest.raises(IndexerResponseError) as exc_info:
        await newznab.fetch_nzb(
            "secret", "safe", inner_transport=transport, pinned_ip="93.184.216.34"
        )
    assert exc_info.value.code == "indexer_xml_unsafe"


async def test_fetch_nzb_limits_size_and_identifier():
    transport = httpx.MockTransport(
        lambda _: httpx.Response(200, headers={"content-type": "application/x-nzb"}, content=_NZB)
    )
    with pytest.raises(IndexerResponseError):
        await newznab.fetch_nzb(
            "secret", "bad\nguid", inner_transport=transport, pinned_ip="93.184.216.34"
        )
    with pytest.raises(IndexerResponseError) as exc_info:
        await newznab.fetch_nzb(
            "secret", "safe", inner_transport=transport, pinned_ip="93.184.216.34", max_bytes=10
        )
    assert exc_info.value.code == "indexer_response_too_large"


def _decision(*, eligible=True):
    return ProfileDecision(
        release=RawRelease("Film.German.1080p", "server-guid", 2140, 1, "de", None, "https://evil.invalid/nzb"),
        media_type="movie", decision="eligible" if eligible else "rejected",
        reasons=(), language="de", resolution="1080p", format=None,
        bitrate_kbps=None, score=100,
    )


async def test_service_download_uses_owned_eligible_result_and_ignores_stored_url(monkeypatch):
    store = ResultStore(ttl_seconds=60)
    result_id = store.put("alice", _decision(), now=100)
    seen = []
    monkeypatch.setattr(nzb_service, "RESULTS", store)
    monkeypatch.setattr(nzb_service, "resolve_indexer_api_key", lambda _: "key")

    async def fake_fetch(key, guid):
        seen.append((key, guid))
        return _NZB

    monkeypatch.setattr(nzb_service.newznab, "fetch_nzb", fake_fetch)
    data = await nzb_service.download_result_nzb("alice", result_id, now=101)

    assert data == _NZB
    assert seen == [("key", "server-guid")]
    with pytest.raises(IndexerResponseError):
        await nzb_service.download_result_nzb("bob", result_id, now=101)
