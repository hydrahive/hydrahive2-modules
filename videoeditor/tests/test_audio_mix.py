"""Audio-Mix-Graph-Bau (SPEC-AUDIO.md Schritt 3), reine String-Konstruktion.

Kein ffmpeg-Aufruf — prüft den filter_complex-Graph + Input-Zählung/-Reihenfolge.
"""
from __future__ import annotations

from pathlib import Path

from backend._audio_mix import (
    active_tracks,
    build_filtergraph,
    include_original,
    mix_input_files,
)
from backend.models import EDL, AudioClip, AudioTrack, Clip, OriginalAudio


def _edl(**kw) -> EDL:
    kw.setdefault("file_id", "f")
    kw.setdefault("timeline", [Clip(id="v", src_start=0, src_end=10)])
    return EDL(**kw)


def _clip(cid="a", src="x.mp3", t=0.0, s0=0.0, s1=5.0, **kw) -> AudioClip:
    return AudioClip(id=cid, source_rel=src, t_start=t, src_start=s0, src_end=s1, **kw)


# ---- kein Mix nötig -----------------------------------------------------------

def test_plain_edl_yields_no_graph():
    graph, n = build_filtergraph(_edl())
    assert graph == "" and n == 0


def test_empty_track_yields_no_graph():
    graph, n = build_filtergraph(_edl(audio=[AudioTrack(id="t", clips=[])]))
    assert graph == "" and n == 0


# ---- ein Clip -----------------------------------------------------------------

def test_single_clip_basic_graph():
    edl = _edl(audio=[AudioTrack(id="t", clips=[_clip(s0=1.0, s1=4.0)])])
    graph, n = build_filtergraph(edl)
    assert n == 1                       # ein Audio-Input
    assert "atrim=start=1.000:end=4.000" in graph
    assert "[1:a]" in graph             # Input 1 = erster Clip
    assert "loudnorm" in graph
    assert "[aout]" in graph


def test_clip_delay_when_t_start_positive():
    edl = _edl(audio=[AudioTrack(id="t", clips=[_clip(t=2.5)])])
    graph, _ = build_filtergraph(edl)
    assert "adelay=delays=2500:all=1" in graph


def test_clip_no_delay_at_zero():
    edl = _edl(audio=[AudioTrack(id="t", clips=[_clip(t=0.0)])])
    graph, _ = build_filtergraph(edl)
    assert "adelay" not in graph


def test_clip_gain_and_fades():
    edl = _edl(audio=[AudioTrack(id="t", clips=[
        _clip(t=1.0, s0=0.0, s1=6.0, gain_db=-3.0, fade_in=1.0, fade_out=2.0),
    ])])
    graph, _ = build_filtergraph(edl)
    assert "volume=-3.00dB" in graph
    assert "afade=t=in:st=1.000:d=1.000" in graph
    # fade_out startet bei t_start + dur - fade_out = 1 + 6 - 2 = 5.0
    assert "afade=t=out:st=5.000:d=2.000" in graph


# ---- mehrere Clips / Spuren ---------------------------------------------------

def test_two_clips_one_track_use_amix():
    edl = _edl(audio=[AudioTrack(id="t", clips=[_clip("a", t=0), _clip("b", t=5)])])
    graph, n = build_filtergraph(edl)
    assert n == 2
    assert "amix=inputs=2" in graph


def test_track_gain_applied():
    edl = _edl(audio=[AudioTrack(id="t", gain_db=-6.0, clips=[_clip()])])
    graph, _ = build_filtergraph(edl)
    assert "volume=-6.00dB" in graph


def test_two_tracks_plus_original_mix_count():
    edl = _edl(audio=[
        AudioTrack(id="t1", clips=[_clip("a")]),
        AudioTrack(id="t2", clips=[_clip("b")]),
    ])
    graph, n = build_filtergraph(edl)
    assert n == 2
    # 2 Spuren + O-Ton = amix inputs=3 im finalen Schritt
    assert "amix=inputs=3" in graph


# ---- Mute / Solo --------------------------------------------------------------

def test_original_mute_excludes_orig_from_mix():
    edl = _edl(original_audio=OriginalAudio(mute=True),
               audio=[AudioTrack(id="t", clips=[_clip()])])
    graph, _ = build_filtergraph(edl)
    assert "[0:a]" not in graph          # O-Ton nicht gemappt
    assert include_original(edl) is False


def test_solo_track_isolates_and_excludes_others_and_orig():
    edl = _edl(audio=[
        AudioTrack(id="t1", solo=True, clips=[_clip("a")]),
        AudioTrack(id="t2", clips=[_clip("b")]),
    ])
    assert [t.id for t in active_tracks(edl)] == ["t1"]
    assert include_original(edl) is False
    graph, n = build_filtergraph(edl)
    assert n == 1                        # nur der Solo-Clip


def test_muted_track_dropped_but_others_stay():
    edl = _edl(audio=[
        AudioTrack(id="t1", mute=True, clips=[_clip("a")]),
        AudioTrack(id="t2", clips=[_clip("b")]),
    ])
    assert [t.id for t in active_tracks(edl)] == ["t2"]


def test_original_gain_only_still_builds_graph():
    edl = _edl(original_audio=OriginalAudio(gain_db=-4.0))
    graph, n = build_filtergraph(edl)
    assert n == 0
    assert "[0:a]volume=-4.00dB[orig]" in graph
    assert "loudnorm" in graph


# ---- Input-Datei-Reihenfolge --------------------------------------------------

def test_mix_input_files_order_matches_clip_order():
    edl = _edl(audio=[
        AudioTrack(id="t1", clips=[_clip("a", src="music.mp3")]),
        AudioTrack(id="t2", clips=[_clip("b", src="voice.wav"), _clip("c", src="sfx.mp3")]),
    ])
    files = mix_input_files(edl, lambda rel: Path("/ws") / rel)
    assert files == [Path("/ws/music.mp3"), Path("/ws/voice.wav"), Path("/ws/sfx.mp3")]


def test_mix_input_files_skips_muted_tracks():
    edl = _edl(audio=[
        AudioTrack(id="t1", mute=True, clips=[_clip("a", src="skip.mp3")]),
        AudioTrack(id="t2", clips=[_clip("b", src="keep.mp3")]),
    ])
    files = mix_input_files(edl, lambda rel: Path("/ws") / rel)
    assert files == [Path("/ws/keep.mp3")]
