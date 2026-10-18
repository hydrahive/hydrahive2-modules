"""Studio 6a: Herunterladen als SRT und WebVTT (Dateien entstehen beim Abruf aus den Daten)."""
from __future__ import annotations

from _subtitle_helpers import P, S, cue, put
from _timeline_helpers import _code


def test_srt(client, auth_headers, ws) -> None:
    client.put(f"{P}/screenplay", headers=auth_headers, json={"title": "Der alte Fischer"})
    put(client, auth_headers, [cue(1, 0.5, 2.25, "Eins"), cue(2, 3661.004, 3662, "Zwei\nZeilen")])
    r = client.get(f"{S}/de/export?format=srt", headers=auth_headers)
    assert r.status_code == 200
    out = r.json()
    assert out["filename"] == "Der alte Fischer.de.srt" and out["mime"].startswith("application/x-subrip")
    assert out["content"] == ("1\n00:00:00,500 --> 00:00:02,250\nEins\n\n"
                              "2\n01:01:01,004 --> 01:01:02,000\nZwei\nZeilen\n")


def test_vtt_escapes(client, auth_headers, ws) -> None:
    put(client, auth_headers, [cue(1, 0, 1.5, "A < B & C > D")])
    out = client.get(f"{S}/de/export?format=vtt", headers=auth_headers).json()
    assert out["filename"] == "Film.de.vtt" and out["mime"].startswith("text/vtt")
    assert out["content"] == "WEBVTT\n\n00:00:00.000 --> 00:00:01.500\nA &lt; B &amp; C &gt; D\n"


def test_filename_is_safe(client, auth_headers, ws) -> None:
    client.put(f"{P}/screenplay", headers=auth_headers, json={"title": "../a/b: c*?"})
    put(client, auth_headers, [cue(1, 0, 1)])
    name = client.get(f"{S}/de/export?format=srt", headers=auth_headers).json()["filename"]
    assert "/" not in name and "\\" not in name and ":" not in name and "*" not in name and name.endswith(".de.srt")
    assert not name.startswith(".")


def test_rounding_never_overlaps(client, auth_headers, ws) -> None:
    put(client, auth_headers, [cue(1, 0, 1.0004), cue(2, 1.0004, 2)])
    lines = client.get(f"{S}/de/export?format=srt", headers=auth_headers).json()["content"].split("\n")
    assert lines[1] == "00:00:00,000 --> 00:00:01,000" and lines[5] == "00:00:01,000 --> 00:00:02,000"


def test_errors(client, auth_headers, ws) -> None:
    assert _code(client.get(f"{S}/de/export?format=srt", headers=auth_headers)) == "400 studio_subtitles_empty"
    put(client, auth_headers, [cue(1, 0, 1)])
    assert _code(client.get(f"{S}/de/export?format=doc", headers=auth_headers)) == "400 studio_subtitles_invalid"
