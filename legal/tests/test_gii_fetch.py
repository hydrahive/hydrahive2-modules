"""Laden von gesetze-im-internet.de – nur dieser Host, nur https, Größenlimit, ZIP im Speicher (Plan L1 Schritt 4).

Befund 20.10.2026: gii-toc.xml verlinkt ``http://…/xml.zip`` → 302 auf https. Der Kern-Client folgt Redirects
bewusst nicht (SSRF), daher baut das Modul die https-URL selbst aus dem Kürzel.
"""
from __future__ import annotations

import asyncio
import io
import zipfile

import pytest
from backend import gii_fetch
from conftest import fixture_xml


def _zip(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in files.items():
            z.writestr(name, data)
    return buf.getvalue()


class _Resp:
    def __init__(self, status=200, content=b""):
        self.status_code = status
        self.content = content


@pytest.fixture
def fake_http(monkeypatch):
    calls = []
    answers = {}

    async def get(url):
        calls.append(url)
        return answers.get(url, _Resp(404))

    monkeypatch.setattr(gii_fetch, "_get", get)
    return calls, answers


TOC = b"""<?xml version="1.0" encoding="UTF-8" ?><items>
<item><title>B\xc3\xbcrgerliches Gesetzbuch</title><link>http://www.gesetze-im-internet.de/bgb/xml.zip</link></item>
<item><title>Gesetz &#252;ber Ordnungswidrigkeiten</title><link>http://www.gesetze-im-internet.de/owig_1968/xml.zip</link></item>
<item><title>Fremd</title><link>http://evil.example/x/xml.zip</link></item>
</items>"""


def test_url_is_https_on_the_official_host():
    assert gii_fetch.zip_url("bgb") == "https://www.gesetze-im-internet.de/bgb/xml.zip"
    assert gii_fetch.TOC_URL == "https://www.gesetze-im-internet.de/gii-toc.xml"


@pytest.mark.parametrize("bad", ["../etc", "bgb/../x", "BGB", "b g b", "", "a" * 81, "bgb?x=1", "http://x"])
def test_invalid_keys_are_rejected_without_request(fake_http, bad):
    calls, _ = fake_http
    with pytest.raises(gii_fetch.FetchError):
        asyncio.run(gii_fetch.fetch_law_xml(bad))
    assert calls == []


def test_toc_parses_keys_and_titles_only_from_official_host(fake_http):
    _, answers = fake_http
    answers[gii_fetch.TOC_URL] = _Resp(200, TOC)
    toc = asyncio.run(gii_fetch.fetch_toc())
    assert toc == {"bgb": "Bürgerliches Gesetzbuch", "owig_1968": "Gesetz über Ordnungswidrigkeiten"}


def test_fetch_law_reads_single_xml_from_zip(fake_http):
    calls, answers = fake_http
    answers[gii_fetch.zip_url("bgb")] = _Resp(200, _zip({"BJNR001950896.xml": fixture_xml("bgb")}))
    assert asyncio.run(gii_fetch.fetch_law_xml("bgb")) == fixture_xml("bgb")
    assert calls == ["https://www.gesetze-im-internet.de/bgb/xml.zip"]


@pytest.mark.parametrize("files", [{}, {"a.xml": b"<x/>", "b.xml": b"<y/>"}, {"readme.txt": b"hi"}])
def test_zip_without_exactly_one_xml_is_an_error(fake_http, files):
    _, answers = fake_http
    answers[gii_fetch.zip_url("bgb")] = _Resp(200, _zip(files))
    with pytest.raises(gii_fetch.FetchError):
        asyncio.run(gii_fetch.fetch_law_xml("bgb"))


def test_http_error_and_not_a_zip(fake_http):
    _, answers = fake_http
    answers[gii_fetch.zip_url("bgb")] = _Resp(500, b"")
    with pytest.raises(gii_fetch.FetchError, match="HTTP 500"):
        asyncio.run(gii_fetch.fetch_law_xml("bgb"))
    answers[gii_fetch.zip_url("bgb")] = _Resp(200, b"kein zip")
    with pytest.raises(gii_fetch.FetchError):
        asyncio.run(gii_fetch.fetch_law_xml("bgb"))


def test_too_big_download_or_unpacked_xml_is_rejected(fake_http, monkeypatch):
    _, answers = fake_http
    monkeypatch.setattr(gii_fetch, "MAX_ZIP_BYTES", 100)
    answers[gii_fetch.zip_url("bgb")] = _Resp(200, b"x" * 101)
    with pytest.raises(gii_fetch.FetchError, match="zu groß"):
        asyncio.run(gii_fetch.fetch_law_xml("bgb"))
    monkeypatch.setattr(gii_fetch, "MAX_ZIP_BYTES", 10_000_000)
    monkeypatch.setattr(gii_fetch, "MAX_XML_BYTES", 1000)
    answers[gii_fetch.zip_url("bgb")] = _Resp(200, _zip({"g.xml": b"<a>" + b"x" * 5000 + b"</a>"}))
    with pytest.raises(gii_fetch.FetchError, match="zu groß"):
        asyncio.run(gii_fetch.fetch_law_xml("bgb"))
