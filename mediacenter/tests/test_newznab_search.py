from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest
from pydantic import ValidationError

from backend import newznab, xml_limits
from backend.errors import IndexerResponseError
from backend.models import SearchRequest
from backend.newznab_xml import parse_search


_RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:newznab="http://www.newznab.com/DTD/2010/feeds/attributes/" version="2.0">
  <channel>
    <item>
      <title>Der.Pate.1972.German.1080p.BluRay.x264-GRP</title>
      <guid isPermaLink="false">abc-123</guid>
      <link>https://treasure-maps.com/getnzb/abc-123</link>
      <pubDate>Sat, 26 Jul 2026 10:00:00 +0000</pubDate>
      <category>Movies - DE &gt; HD</category>
      <enclosure url="https://treasure-maps.com/getnzb/abc-123" length="123456789" type="application/x-nzb" />
      <newznab:attr name="category" value="2140" />
      <newznab:attr name="size" value="123456789" />
      <newznab:attr name="language" value="de" />
      <newznab:attr name="guid" value="abc-123" />
    </item>
  </channel>
</rss>
"""


@pytest.mark.parametrize(
    "media_type,expected_t,expected_cat",
    [
        ("movie", "movie", "2140,2145,2150"),
        ("tv", "tvsearch", "5140,5145"),
        ("book", "book", "7120"),
        ("audiobook", "search", "3130"),
        ("audioplay", "search", "3130"),
        ("music", "music", "3010,3040"),
    ],
)
def test_search_params_are_server_controlled(media_type, expected_t, expected_cat):
    request = SearchRequest(query="Beispiel", media_type=media_type, limit=25)

    params = newznab.build_search_params(request)

    assert params == {"t": expected_t, "q": "Beispiel", "cat": expected_cat, "limit": "25"}
    assert "apikey" not in params
    assert "url" not in params


def test_music_search_forwards_artist_and_album():
    request = SearchRequest(
        query="Album", media_type="music", artist="Artist", album="Record"
    )

    params = newznab.build_search_params(request)

    assert params["artist"] == "Artist"
    assert params["album"] == "Record"


def test_search_params_drop_structured_filters_not_advertised_by_caps():
    request = SearchRequest(
        query="Album", media_type="music", artist="Artist", album="Record", year=2024
    )

    params = newznab.build_search_params(request, supported_params={"q", "artist"})

    assert params["artist"] == "Artist"
    assert "album" not in params
    assert "year" not in params


def test_search_params_forward_only_supported_structured_filters():
    request = SearchRequest(
        query="Serie", media_type="tv", year=2024, season=2, episode="03", max_age_days=30
    )

    params = newznab.build_search_params(request)

    assert params["year"] == "2024"
    assert params["season"] == "2"
    assert params["ep"] == "03"
    assert params["maxage"] == "30"


@pytest.mark.parametrize("query", ["", " ", "x", "x" * 201])
def test_search_query_length_is_validated(query):
    with pytest.raises(ValidationError):
        SearchRequest(query=query, media_type="movie")


@pytest.mark.parametrize(
    "media_type,field,value",
    [
        ("movie", "album", "Record"),
        ("music", "season", 2),
        ("tv", "artist", "Artist"),
        ("audioplay", "author", "Writer"),
    ],
)
def test_media_specific_filters_are_validated(media_type, field, value):
    with pytest.raises(ValidationError):
        SearchRequest(query="Beispiel", media_type=media_type, **{field: value})


def test_size_range_is_validated():
    with pytest.raises(ValidationError):
        SearchRequest(query="Film", media_type="movie", min_size_mb=2000, max_size_mb=1000)


def test_parse_search_extracts_only_bounded_internal_fields():
    releases = parse_search(_RSS, max_items=10)

    assert len(releases) == 1
    release = releases[0]
    assert release.title == "Der.Pate.1972.German.1080p.BluRay.x264-GRP"
    assert release.guid == "abc-123"
    assert release.category_id == 2140
    assert release.size_bytes == 123456789
    assert release.language == "de"
    assert release.published_at == datetime(2026, 7, 26, 10, 0, tzinfo=timezone.utc)
    assert release.download_url == "https://treasure-maps.com/getnzb/abc-123"


def test_parse_search_rejects_excessive_xml_depth(monkeypatch):
    monkeypatch.setattr(xml_limits, "MAX_XML_DEPTH", 4)
    xml = b"<rss><channel><a><b><c /></b></a></channel></rss>"

    with pytest.raises(IndexerResponseError) as exc_info:
        parse_search(xml)

    assert exc_info.value.code == "indexer_xml_too_complex"


def test_parse_search_rejects_excessive_element_count(monkeypatch):
    monkeypatch.setattr(xml_limits, "MAX_XML_ELEMENTS", 3)

    with pytest.raises(IndexerResponseError) as exc_info:
        parse_search(b"<rss><channel><a /><b /></channel></rss>")

    assert exc_info.value.code == "indexer_xml_too_complex"


def test_parse_search_rejects_non_rss_shape():
    with pytest.raises(IndexerResponseError) as exc_info:
        parse_search(b"<caps />")

    assert exc_info.value.code == "indexer_search_invalid"


def test_parse_search_skips_item_with_missing_identity():
    xml = b"<rss><channel><item><title>Only title</title></item></channel></rss>"
    assert parse_search(xml) == []


@pytest.mark.parametrize(
    "external",
    [
        b"http://127.0.0.1/private",
        b"https://file.treasure-maps.com.evil.invalid/getnzb/abc-123",
        b"https://evil-treasure-maps.com/getnzb/abc-123",
    ],
)
def test_parse_search_marks_external_download_url_unusable(external):
    xml = _RSS.replace(b"https://treasure-maps.com/getnzb/abc-123", external)
    release = parse_search(xml)[0]

    assert release.download_url is None


def test_parse_search_accepts_exact_treasure_maps_file_origin():
    source = b"https://treasure-maps.com/getnzb/abc-123"
    file_origin = b"https://file.treasure-maps.com/getnzb/abc-123?r=opaque"

    release = parse_search(_RSS.replace(source, file_origin))[0]

    assert release.download_url == "https://file.treasure-maps.com/getnzb/abc-123"


@pytest.mark.parametrize(
    "bad_url",
    [
        b"https://treasure-maps.com:bad/getnzb/abc-123",
        b"https://treasure-maps.com:99999/getnzb/abc-123",
        b"https://[broken/getnzb/abc-123",
    ],
)
def test_parse_search_marks_malformed_download_url_unusable(bad_url):
    xml = _RSS.replace(b"https://treasure-maps.com/getnzb/abc-123", bad_url)

    assert parse_search(xml)[0].download_url is None


def test_parse_search_rejects_download_url_with_raw_whitespace():
    bad_url = b"https://treasure-maps.com/\ngetnzb/abc-123"
    xml = _RSS.replace(b"https://treasure-maps.com/getnzb/abc-123", bad_url)

    assert parse_search(xml)[0].download_url is None


def test_parse_search_strips_api_key_from_internal_download_url():
    with_secret = b"https://treasure-maps.com/getnzb/abc-123?id=abc&amp;apikey=SECRET"
    xml = _RSS.replace(b"https://treasure-maps.com/getnzb/abc-123", with_secret)
    release = parse_search(xml)[0]

    assert release.download_url == "https://treasure-maps.com/getnzb/abc-123"
    assert "SECRET" not in release.download_url


def test_parse_search_handles_invalid_size_and_date_without_crashing():
    xml = _RSS.replace(b"123456789", b"not-a-number").replace(
        b"Sat, 26 Jul 2026 10:00:00 +0000", b"not-a-date"
    )
    release = parse_search(xml)[0]

    assert release.size_bytes is None
    assert release.published_at is None


def test_parse_search_skips_duplicate_newznab_attributes():
    duplicate = b'<newznab:attr name="language" value="en" />'
    xml = _RSS.replace(b"</item>", duplicate + b"</item>")

    assert parse_search(xml) == []


async def test_search_uses_caps_to_gate_structured_parameters():
    caps_xml = b"""<caps><limits max="500" default="250"/><searching>
      <search available="yes" supportedParams="q"/>
      <music-search available="yes" supportedParams="q,artist"/>
    </searching><categories><category id="3010"/></categories></caps>"""
    captured: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        content = caps_xml if request.url.params["t"] == "caps" else _RSS
        return httpx.Response(200, headers={"content-type": "text/xml"}, content=content)

    await newznab.search(
        "secret",
        SearchRequest(
            query="Album", media_type="music", artist="Artist", album="Record"
        ),
        inner_transport=httpx.MockTransport(handler),
        pinned_ip="93.184.216.34",
    )

    assert len(captured) == 2
    search_request = captured[1]
    assert search_request.url.params["artist"] == "Artist"
    assert "album" not in search_request.url.params


@pytest.mark.parametrize(
    "encoding", ["plain", "xml_entities", "url_encoded", "triple_url_encoded"]
)
async def test_search_drops_release_that_echoes_api_key(encoding):
    secret = "never-return-this-key"
    payload = secret
    if encoding == "xml_entities":
        payload = "".join(f"&#{ord(character)};" for character in secret)
    elif encoding == "url_encoded":
        payload = secret.replace("-", "%2D")
    elif encoding == "triple_url_encoded":
        payload = secret.replace("-", "%25252D")
    xml = _RSS.replace(
        b"Der.Pate.1972.German.1080p.BluRay.x264-GRP", payload.encode()
    )
    transport = httpx.MockTransport(
        lambda _: httpx.Response(
            200, headers={"content-type": "application/rss+xml"}, content=xml
        )
    )

    releases = await newznab.search(
        secret,
        SearchRequest(query="Film", media_type="movie"),
        inner_transport=transport,
        pinned_ip="93.184.216.34",
    )

    assert releases == []


async def test_search_accepts_api_key_only_in_upstream_download_url():
    secret = "normal-newznab-key"
    with_secret = (
        b"https://treasure-maps.com/getnzb/abc-123?id=abc&amp;apikey="
        + secret.encode()
    )
    xml = _RSS.replace(b"https://treasure-maps.com/getnzb/abc-123", with_secret)
    transport = httpx.MockTransport(
        lambda _: httpx.Response(
            200, headers={"content-type": "application/rss+xml"}, content=xml
        )
    )

    releases = await newznab.search(
        secret,
        SearchRequest(query="Film", media_type="movie"),
        inner_transport=transport,
        pinned_ip="93.184.216.34",
    )

    assert len(releases) == 1
    assert releases[0].download_url == "https://treasure-maps.com/getnzb/abc-123"
    assert secret not in str(releases[0])


async def test_search_calls_newznab_and_parses_releases():
    captured: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, headers={"content-type": "application/rss+xml"}, content=_RSS)

    request = SearchRequest(query="Der Pate", media_type="movie", limit=5)
    releases = await newznab.search(
        "secret",
        request,
        inner_transport=httpx.MockTransport(handler),
        pinned_ip="93.184.216.34",
    )

    assert len(releases) == 1
    assert captured[0].url.params["t"] == "movie"
    assert captured[0].url.params["cat"] == "2140,2145,2150"
    assert captured[0].url.params["apikey"] == "secret"
