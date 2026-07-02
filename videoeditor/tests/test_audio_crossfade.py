"""Crossfade-Ableitung aus Clip-Überlappung (SPEC-AUDIO.md Schritt 5).

Reine Logik: überlappen sich zwei Clips einer Spur, wird der frühere aus- und
der spätere über die Überlappungszone eingeblendet (amix addiert -> Crossfade).
Nutzer-Fades bleiben Untergrenze.
"""
from __future__ import annotations

from backend._audio_mix import build_filtergraph, crossfade_durations
from backend.models import EDL, AudioClip, AudioTrack, Clip


def _clip(cid, t, s0=0.0, s1=5.0, fin=0.0, fout=0.0):
    return AudioClip(id=cid, source_rel="x.mp3", t_start=t, src_start=s0, src_end=s1,
                     fade_in=fin, fade_out=fout)


def test_no_overlap_keeps_user_fades():
    clips = [_clip("a", 0, s1=4, fout=1.0), _clip("b", 10, s1=4, fin=0.5)]
    f = crossfade_durations(clips)
    assert f["a"] == (0.0, 1.0)
    assert f["b"] == (0.5, 0.0)


def test_overlap_creates_symmetric_crossfade():
    # a: 0..4, b startet bei 3 -> 1s Überlappung
    clips = [_clip("a", 0, s1=4), _clip("b", 3, s1=4)]
    f = crossfade_durations(clips)
    assert f["a"][1] == 1.0   # a fadet über 1s aus
    assert f["b"][0] == 1.0   # b fadet über 1s ein


def test_crossfade_does_not_shorten_user_fade():
    # Nutzer hat 2s fade_out gesetzt, Überlappung nur 1s -> 2s bleibt
    clips = [_clip("a", 0, s1=4, fout=2.0), _clip("b", 3, s1=4)]
    f = crossfade_durations(clips)
    assert f["a"][1] == 2.0


def test_crossfade_limited_by_clip_length():
    # b ist nur 0.5s lang -> Crossfade max 0.5s obwohl Überlappung größer
    clips = [_clip("a", 0, s1=5), _clip("b", 1, s0=0, s1=0.5)]
    f = crossfade_durations(clips)
    assert f["b"][0] <= 0.5
    assert f["a"][1] <= 0.5


def test_order_independent():
    """Reihenfolge in der Liste egal — sortiert wird nach t_start."""
    a = _clip("a", 0, s1=4)
    b = _clip("b", 3, s1=4)
    assert crossfade_durations([b, a]) == crossfade_durations([a, b])


def test_three_clips_chain():
    clips = [_clip("a", 0, s1=4), _clip("b", 3, s1=4), _clip("c", 6, s1=4)]
    f = crossfade_durations(clips)
    assert f["a"][1] == 1.0            # a->b
    assert f["b"] == (1.0, 1.0)        # ein aus a, aus nach c
    assert f["c"][0] == 1.0            # b->c


def test_graph_includes_crossfade_fades():
    """Der gebaute Graph zeigt die abgeleiteten Fades (afade in/out)."""
    edl = EDL(
        file_id="f",
        timeline=[Clip(id="v", src_start=0, src_end=10)],
        audio=[AudioTrack(id="t", clips=[_clip("a", 0, s1=4), _clip("b", 3, s1=4)])],
    )
    graph, _ = build_filtergraph(edl)
    assert "afade=t=out" in graph   # a blendet aus
    assert "afade=t=in" in graph    # b blendet ein
