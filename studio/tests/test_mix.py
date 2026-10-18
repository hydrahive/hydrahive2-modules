"""Studio 5b: Mischpult – Prüfregeln, Ducking-Kurve, Mix-Graph (studio/SPEC.md „Bauplan 5b“). Ohne ffmpeg-Aufruf."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from _timeline_helpers import T, _aclip, _audio, _code

from backend import mix
from backend import render_args as ra

TABLE = json.loads((Path(__file__).parent / "duck_table.json").read_text())
BASE = Path("/proj")


def _put(client, h, tracks: list[dict], revision: int = 0, **extra):
    return client.put(T, headers=h, json={"revision": revision, "fps": 25, "tracks": tracks, **extra})


def _tr(v=None, a1=None, a2=None, **kw):
    out = [{"id": "V1", "kind": "video", "clips": v or [], **kw.get("V1", {})},
           {"id": "A1", "kind": "audio", "clips": a1 or [], **kw.get("A1", {})},
           {"id": "A2", "kind": "audio", "clips": a2 or [], **kw.get("A2", {})}]
    return out


def test_mixer_values_are_saved_only_when_not_default(client, auth_headers, ws) -> None:
    m = _audio(ws, "lied.mp3")
    c = _aclip(id="1" * 32, out=6, media_rel=m, gain_db=-6.5, fade_in=1, fade_out=0.5)
    r = _put(client, auth_headers, _tr(a2=[c], V1={"gain_db": -3, "mute": True}, A2={"solo": True}), duck=False)
    assert r.status_code == 200, r.text
    tl = client.get(T, headers=auth_headers).json()
    v1, a1, a2 = tl["tracks"]
    assert (v1.get("gain_db"), v1.get("mute"), a2.get("solo")) == (-3, True, True)
    assert "gain_db" not in a1 and "mute" not in a1 and "solo" not in a1        # Standard wird nicht gespeichert
    assert a2["clips"][0]["gain_db"] == -6.5 and a2["clips"][0]["fade_in"] == 1 and a2["clips"][0]["fade_out"] == 0.5
    assert tl["duck"] is False
    r2 = _put(client, auth_headers, _tr(a2=[_aclip(id="1" * 32, out=6, media_rel=m, gain_db=0, fade_in=0)]), 1, duck=True)
    saved = json.loads((ws / "studio/timelines/main.json").read_text())
    assert "duck" not in saved and "gain_db" not in saved["tracks"][2]["clips"][0] and "fade_in" not in saved["tracks"][2]["clips"][0]
    assert r2.json()["duck"] is True                                             # Antwort nennt den Standard


def test_mixer_rules(client, auth_headers, ws) -> None:
    m = _audio(ws, "lied.mp3")
    bad = {
        "Spur zu laut": _tr(V1={"gain_db": 12.5}),
        "Spur zu leise": _tr(A1={"gain_db": -61}),
        "Spur Text": _tr(A1={"gain_db": "3"}),
        "Stumm als Zahl": _tr(A2={"mute": 1}),
        "Solo als Text": _tr(A2={"solo": "ja"}),
        "Clip zu laut": _tr(a2=[_aclip(media_rel=m, gain_db=13)]),
        "Blende negativ": _tr(a2=[_aclip(media_rel=m, fade_in=-1)]),
        "Blenden länger als Clip": _tr(a2=[_aclip(media_rel=m, out=4, fade_in=3, fade_out=1.5)]),
        "Blende als Wahrheitswert": _tr(a2=[_aclip(media_rel=m, fade_out=True)]),
    }
    for name, tracks in bad.items():
        assert _code(_put(client, auth_headers, tracks)) == "400 studio_timeline_invalid", name
    assert _code(_put(client, auth_headers, _tr(), duck="ja")) == "400 studio_timeline_invalid"
    assert _put(client, auth_headers, _tr(a2=[_aclip(media_rel=m, out=4, fade_in=2, fade_out=2, gain_db=12)],
                                          A1={"gain_db": -60})).status_code == 200      # Grenzen gehen


def test_broken_mixer_values_in_file_fall_back(client, auth_headers, ws) -> None:
    m = _audio(ws, "lied.mp3")
    (ws / "studio/timelines").mkdir(parents=True)
    (ws / "studio/timelines/main.json").write_text(json.dumps({"revision": 2, "fps": 25, "duck": "x", "tracks": [
        {"id": "V1", "clips": [], "gain_db": 99, "mute": "x"},
        {"id": "A2", "clips": [_aclip(id="1" * 32, media_rel=m, out=4, gain_db="laut", fade_in=9)], "solo": True}]}))
    tl = client.get(T, headers=auth_headers).json()
    assert "gain_db" not in tl["tracks"][0] and "mute" not in tl["tracks"][0] and tl["tracks"][2]["solo"] is True
    c = tl["tracks"][2]["clips"][0]
    assert "gain_db" not in c and "fade_in" not in c and tl["duck"] is True
    assert client.put(T, headers=auth_headers, json=tl).status_code == 200            # so wieder speicherbar


def test_audible_tracks_solo_and_mute() -> None:
    tracks = {"V1": {}, "A1": {"mute": True}, "A2": {}}
    assert mix.audible(tracks) == {"V1", "A2"}
    assert mix.audible({"V1": {}, "A1": {"solo": True}, "A2": {"solo": True, "mute": True}}) == {"A1", "A2"}   # Solo schlägt Stumm
    assert mix.audible({"V1": {"mute": True}, "A1": {"mute": True}, "A2": {"mute": True}}) == set()


def test_duck_spans_merge_and_limit() -> None:
    assert mix.duck_spans(TABLE["spans"]) == TABLE["merged"]
    assert mix.duck_spans([]) == []
    many = [[i * 2.0, i * 2.0 + 0.5] for i in range(500)]
    assert len(mix.duck_spans(many)) <= mix.MAX_SPANS


@pytest.mark.parametrize(("t", "want"), TABLE["points"])
def test_duck_curve_matches_table(t, want) -> None:
    assert mix.duck_factor(TABLE["merged"], t) == pytest.approx(want, abs=2e-3)


def test_duck_expression_is_the_same_curve() -> None:
    expr = mix.duck_expr(TABLE["merged"])
    for t, want in TABLE["points"]:
        got = eval(expr.replace("t", f"({t})").replace("min(", "min(").replace("max(", "max(").replace("if(", "_if("),  # noqa: S307
                   {"_if": lambda c, a, b: a if c else b, "min": min, "max": max, "lt": lambda a, b: a < b, "gte": lambda a, b: a >= b})
        assert got == pytest.approx(want, abs=2e-3), t
    assert mix.duck_expr([]) == "1"


def _graph(cmd):
    return cmd[cmd.index("-filter_complex") + 1]


def test_graph_without_mixer_is_unchanged() -> None:
    segs = [{"kind": "image", "seconds": 4, "media": "b.png"}]
    parts = [{"start": 0, "in": 0, "seconds": 2, "media": "m.wav", "track": "A2"}]
    plain = ra.command(segs, BASE, Path("/o.mp4"), size=(320, 240), fps=25, audio=parts)
    assert _graph(plain) == _graph(ra.command(segs, BASE, Path("/o.mp4"), size=(320, 240), fps=25, audio=parts, mixer=mix.Mixer()))
    assert "volume" not in _graph(plain) and "afade" not in _graph(plain)


def test_graph_gain_fades_and_original_sound() -> None:
    segs = [{"kind": "image", "seconds": 6, "media": "b.png"}]
    parts = [{"start": 1, "in": 0, "seconds": 4, "media": "m.wav", "track": "A2", "gain_db": -6, "fade_in": 1, "fade_out": 0.5}]
    mx = mix.Mixer(tracks={"V1": {"gain_db": -3}, "A1": {}, "A2": {"gain_db": 2}})
    g = _graph(ra.command(segs, BASE, Path("/o.mp4"), size=(320, 240), fps=25, audio=parts, mixer=mx))
    assert "afade=t=in:st=0:d=1.000" in g and "afade=t=out:st=3.500:d=0.500" in g
    assert "volume=-4.00dB" in g                                     # Clip −6 + Spur +2
    assert "[a0]volume=-3.00dB" in g                                  # Originalton −3


def test_graph_mute_solo_and_silent_original() -> None:
    segs = [{"kind": "image", "seconds": 4, "media": "b.png"}]
    parts = [{"start": 0, "in": 0, "seconds": 2, "media": "s.wav", "track": "A1"}, {"start": 0, "in": 0, "seconds": 4, "media": "m.wav", "track": "A2"}]
    cmd = ra.command(segs, BASE, Path("/o.mp4"), size=(320, 240), fps=25, audio=parts, mixer=mix.Mixer(tracks={"V1": {}, "A1": {"mute": True}, "A2": {}}))
    assert "/proj/s.wav" not in cmd and "/proj/m.wav" in cmd           # stumme Spur fällt ganz weg
    solo = ra.command(segs, BASE, Path("/o.mp4"), size=(320, 240), fps=25, audio=parts, mixer=mix.Mixer(tracks={"V1": {}, "A1": {"solo": True}, "A2": {}}))
    g = _graph(solo)
    assert "/proj/m.wav" not in solo and "/proj/s.wav" in solo and "[a0]volume=0" in g     # Originalton ohne Solo → stumm


def test_graph_ducking_only_with_voice_and_music() -> None:
    segs = [{"kind": "image", "seconds": 6, "media": "b.png"}]
    voice = {"start": 2, "in": 0, "seconds": 2, "media": "s.wav", "track": "A1"}
    music = {"start": 0, "in": 0, "seconds": 6, "media": "m.wav", "track": "A2"}
    g = _graph(ra.command(segs, BASE, Path("/o.mp4"), size=(320, 240), fps=25, audio=[voice, music], mixer=mix.Mixer()))
    assert "eval=frame" in g and g.count("volume='") == 1
    no_voice = _graph(ra.command(segs, BASE, Path("/o.mp4"), size=(320, 240), fps=25, audio=[music], mixer=mix.Mixer()))
    assert "eval=frame" not in no_voice
    off = _graph(ra.command(segs, BASE, Path("/o.mp4"), size=(320, 240), fps=25, audio=[voice, music], mixer=mix.Mixer(duck=False)))
    assert "eval=frame" not in off
    muted_voice = _graph(ra.command(segs, BASE, Path("/o.mp4"), size=(320, 240), fps=25, audio=[voice, music],
                                    mixer=mix.Mixer(tracks={"V1": {}, "A1": {"mute": True}, "A2": {}})))
    assert "eval=frame" not in muted_voice                          # stumme Sprache duckt nicht
