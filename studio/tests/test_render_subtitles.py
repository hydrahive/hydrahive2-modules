"""Studio 6c: Untertitel als abschaltbare Spuren im Film (mov_text, nie eingebrannt). Echter ffmpeg-Lauf."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from _render_helpers import R, clip, make_image, needs_ffmpeg, put_timeline, wait_render
from _subtitle_helpers import P, cue, put

from backend import render_args as ra


def _streams(path) -> list[dict]:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=index,codec_type,codec_name:stream_tags=language:stream_disposition=default",
                          "-of", "json", str(path)], capture_output=True, text=True, timeout=30, check=True).stdout
    return json.loads(out)["streams"]


def test_command_adds_subtitle_tracks_after_everything_else() -> None:
    segs = [{"kind": "gap", "seconds": 2}]
    plain = ra.command(segs, Path("/p"), Path("/o.mp4"), size=(320, 180), fps=25)
    assert "-c:s" not in plain and "mov_text" not in plain
    subs = [{"file": Path("/t/de.srt"), "language": "de"}, {"file": Path("/t/en.srt"), "language": "en"}]
    cmd = ra.command(segs, Path("/p"), Path("/o.mp4"), size=(320, 180), fps=25, subtitles=subs, default_language="de")
    joined = " ".join(cmd)
    assert "-i /t/de.srt" in joined and "-i /t/en.srt" in joined
    i_de, i_en = cmd.index("/t/de.srt"), cmd.index("/t/en.srt")
    n_inputs = cmd.count("-i")
    assert cmd[cmd.index("-c:s") + 1] == "mov_text"
    assert f"{n_inputs - 2}:0" in cmd and f"{n_inputs - 1}:0" in cmd and i_de < i_en
    assert "language=ger" in cmd and "language=eng" in cmd
    assert cmd[cmd.index("-disposition:s:0") + 1] == "default" and cmd[cmd.index("-disposition:s:1") + 1] == "0"
    assert "subtitles=" not in joined and "drawtext" not in joined                       # nie eingebrannt
    assert cmd[-1] == "/o.mp4"


def test_iso_codes() -> None:
    from backend._clean import LANGUAGES
    from backend.subtitle_format import iso639_2
    assert all(len(iso639_2(lang)) == 3 and iso639_2(lang) != "und" for lang in LANGUAGES)
    assert iso639_2("de") == "ger" and iso639_2("zh") == "chi" and iso639_2("uk") == "ukr" and iso639_2("xx") == "und"


@needs_ffmpeg
def test_render_with_subtitles(client, auth_headers, ws) -> None:
    img = make_image(ws, "a.png", "160x90")
    put_timeline(client, auth_headers, [clip("image", 0, 0, 3, img)])
    client.put(f"{P}/screenplay", headers=auth_headers, json={"language": "de"})
    put(client, auth_headers, [cue(1, 0.5, 1.5, "Hallo Welt")])
    put(client, auth_headers, [cue(1, 0.5, 1.5, "Hello world")], lang="en")
    put(client, auth_headers, [], lang="fr")                            # leer → keine Spur
    r = client.post(f"{R}/render", headers=auth_headers, json={"subtitles": True})
    assert r.status_code == 202, r.text
    job = wait_render(client, auth_headers)
    assert job["status"] == "done", job
    assert job["result"]["subtitles"] == ["de", "en"]
    f = ws / job["result"]["rel"]
    subs = [s for s in _streams(f) if s["codec_type"] == "subtitle"]
    assert [(s["codec_name"], s["tags"]["language"], s["disposition"]["default"]) for s in subs] == [("mov_text", "ger", 1), ("mov_text", "eng", 0)]
    srt = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(f), "-map", "0:s:1", "-f", "srt", "-"], capture_output=True, text=True, timeout=30, check=True).stdout
    assert "Hello world" in srt and "00:00:00,500 --> 00:00:01,500" in srt
    meta = json.loads((ws / f"{job['result']['rel']}.json").read_text())
    assert meta["subtitles"] == ["de", "en"]
    assert client.get(f"{R}/renders", headers=auth_headers).json()["renders"][0]["subtitles"] == ["de", "en"]


@needs_ffmpeg
def test_render_without_the_box_has_no_subtitles(client, auth_headers, ws) -> None:
    img = make_image(ws, "a.png", "160x90")
    put_timeline(client, auth_headers, [clip("image", 0, 0, 2, img)])
    put(client, auth_headers, [cue(1, 0.5, 1.5, "Hallo")])
    for body in ({}, {"subtitles": "ja"}, None):
        client.post(f"{R}/render", headers=auth_headers, **({"json": body} if body is not None else {}))
        job = wait_render(client, auth_headers)
        assert job["status"] == "done" and job["result"]["subtitles"] == []
        assert not [s for s in _streams(ws / job["result"]["rel"]) if s["codec_type"] == "subtitle"]


@needs_ffmpeg
def test_render_with_box_but_no_subtitles_is_fine(client, auth_headers, ws) -> None:
    img = make_image(ws, "a.png", "160x90")
    put_timeline(client, auth_headers, [clip("image", 0, 0, 2, img)])
    client.post(f"{R}/render", headers=auth_headers, json={"subtitles": True})
    job = wait_render(client, auth_headers)
    assert job["status"] == "done" and job["result"]["subtitles"] == []
