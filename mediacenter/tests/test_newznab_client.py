from __future__ import annotations

import logging

import httpx
import pytest

from backend import newznab
from backend.errors import IndexerResponseError, IndexerUnavailable

_CAPS_XML = b"""<?xml version="1.0"?>
<caps>
  <limits max="500" default="250" />
  <searching>
    <search available="yes" supportedParams="q" />
    <movie-search available="yes" supportedParams="q,year" />
    <tv-search available="yes" supportedParams="q,season,ep" />
    <music-search available="yes" supportedParams="q,artist" />
    <book-search available="yes" supportedParams="q,author" />
  </searching>
  <categories>
    <category id="2100" name="Movies - DE"><subcat id="2140" name="HD" /></category>
    <category id="3000" name="Audio"><subcat id="3130" name="Audiobook - DE" /></category>
  </categories>
</caps>
"""


async def test_caps_injects_key_only_on_wire_request_and_not_logs(caplog):
    captured: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, headers={"content-type": "text/xml"}, content=_CAPS_XML)

    caplog.set_level(logging.INFO, logger="httpx")
    caps = await newznab.fetch_caps(
        "top-secret-key",
        inner_transport=httpx.MockTransport(handler),
        pinned_ip="93.184.216.34",
    )

    assert caps.max_limit == 500
    assert caps.default_limit == 250
    assert caps.search_types == {"search", "movie", "tv", "music", "book"}
    assert caps.categories == {2100, 2140, 3000, 3130}
    assert len(captured) == 1
    assert captured[0].url.params["apikey"] == "top-secret-key"
    assert captured[0].headers["host"] == "treasure-maps.com"
    assert "top-secret-key" not in caplog.text


@pytest.mark.parametrize("status", [301, 302, 307, 308])
async def test_redirects_are_rejected(status):
    transport = httpx.MockTransport(
        lambda _: httpx.Response(status, headers={"location": "http://127.0.0.1/private"})
    )

    with pytest.raises(IndexerResponseError) as exc_info:
        await newznab.fetch_caps("secret", inner_transport=transport, pinned_ip="93.184.216.34")

    assert exc_info.value.code == "indexer_redirect_rejected"
    assert "127.0.0.1" not in str(exc_info.value)


async def test_decompressed_response_size_is_limited():
    transport = httpx.MockTransport(
        lambda _: httpx.Response(200, headers={"content-type": "text/xml"}, content=b"x" * 101)
    )

    with pytest.raises(IndexerResponseError) as exc_info:
        await newznab.fetch_caps(
            "secret", inner_transport=transport, pinned_ip="93.184.216.34", max_bytes=100
        )

    assert exc_info.value.code == "indexer_response_too_large"


async def test_network_exception_is_mapped_without_secret():
    secret = "never-leak-me"

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"failed with {secret}", request=request)

    with pytest.raises(IndexerUnavailable) as exc_info:
        await newznab.fetch_caps(
            secret, inner_transport=httpx.MockTransport(handler), pinned_ip="93.184.216.34"
        )

    assert exc_info.value.code == "indexer_unavailable"
    assert secret not in str(exc_info.value)
    assert secret not in repr(exc_info.value)


async def test_unexpected_content_type_is_rejected():
    transport = httpx.MockTransport(
        lambda _: httpx.Response(200, headers={"content-type": "text/html"}, content=b"<html />")
    )

    with pytest.raises(IndexerResponseError) as exc_info:
        await newznab.fetch_caps("secret", inner_transport=transport, pinned_ip="93.184.216.34")

    assert exc_info.value.code == "indexer_content_type_invalid"


async def test_doctype_is_rejected_before_xml_parse():
    malicious = b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY e "boom">]><caps>&e;</caps>'
    transport = httpx.MockTransport(
        lambda _: httpx.Response(200, headers={"content-type": "text/xml"}, content=malicious)
    )

    with pytest.raises(IndexerResponseError) as exc_info:
        await newznab.fetch_caps("secret", inner_transport=transport, pinned_ip="93.184.216.34")

    assert exc_info.value.code == "indexer_xml_unsafe"
