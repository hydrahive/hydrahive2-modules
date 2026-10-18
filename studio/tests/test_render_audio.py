"""Studio 5a: Tonspuren in der Ausgabe – Argumente als reine Funktion und echter ffmpeg-Lauf (Spec „Bauplan Etappe 5“)."""
from __future__ import annotations

from pathlib import Path

from _render_helpers import (
    R,
    clip,
    make_audio,
    make_image,
    make_video,
    max_volume,
    needs_ffmpeg,
    probe,
    put_tracks,
    wait_render,
)

from backend import render_args as ra

BASE = Path("/proj")


def _a(start, t_in, t_out, media="m.wav", **kw):
    return {"kind": "audio", "start": start, "in": t_in, "out": t_out, "media_rel": media, "label": "x", **kw}


def test_audio_parts_skip_missing_files_and_missing_clips() -> None:
    parts = ra.audio_parts([_a(2, 1, 4), _a(0, 0, 1, "weg.wav"), _a(5, 0, 1, "", missing=True), _a(0.5, 0, 1, "b.wav")],
                           exists=lambda rel: rel in ("m.wav", "b.wav"))
    assert parts == [{"start": 0.5, "in": 0, "seconds": 1, "media": "b.wav"}, {"start": 2, "in": 1, "seconds": 3, "media": "m.wav"}]


def test_pad_to_appends_black_until_the_last_sound() -> None:
    segs = [{"kind": "image", "seconds": 2, "media": "b.png"}]
    assert ra.pad_to(segs, 5) == [*segs, {"kind": "gap", "seconds": 3}]
    assert ra.pad_to(segs, 2.0004) == segs                                 # Gleitkomma-Rest zählt nicht
    assert ra.pad_to([], 4) == [{"kind": "gap", "seconds": 4}]           # nur Ton → schwarzer Film
    assert ra.audio_end([{"start": 2, "in": 1, "seconds": 3, "media": "m"}]) == 5 and ra.audio_end([]) == 0


def test_command_mixes_audio_parts_at_their_place() -> None:
    segs = [{"kind": "image", "seconds": 4, "media": "b.png"}]
    parts = [{"start": 1.5, "in": 2, "seconds": 2, "media": "m.wav"}, {"start": 0, "in": 0, "seconds": 1, "media": "s.wav"}]
    cmd = ra.command(segs, BASE, Path("/o.mp4"), size=(320, 240), fps=25, audio=parts)
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert "concat=n=1:v=1:a=1[v][a0]" in graph
    assert "adelay=1500:all=1" in graph and "adelay=0:all=1" in graph
    assert "amix=inputs=3:normalize=0:duration=first" in graph and "alimiter" in graph and graph.endswith("[a]")
    i = cmd.index("/proj/m.wav")
    assert cmd[i - 5:i + 1] == ["-ss", "2.000", "-t", "2.000", "-i", "/proj/m.wav"]
    assert cmd[cmd.index("-map") + 1: cmd.index("-map") + 4] == ["[v]", "-map", "[a]"]


def test_command_without_audio_stays_as_in_4d() -> None:
    segs = [{"kind": "image", "seconds": 1, "media": "b.png"}]
    assert ra.command(segs, BASE, Path("/o.mp4"), size=(320, 240), fps=25, audio=[]) == ra.command(segs, BASE, Path("/o.mp4"), size=(320, 240), fps=25)


def test_audio_outside_the_project_is_refused() -> None:
    import pytest
    with pytest.raises(ValueError):
        ra.command([{"kind": "gap", "seconds": 1}], BASE, Path("/o.mp4"), size=(320, 240), fps=25,
                   audio=[{"start": 0, "in": 0, "seconds": 1, "media": "../x.wav"}])


@needs_ffmpeg
def test_render_with_music_reaching_past_the_picture(client, auth_headers, ws) -> None:
    v = make_video(ws, "stumm.mp4", 2, audio=False)
    m = make_audio(ws, "lied.wav", 6)
    put_tracks(client, auth_headers, [clip("video", 0, 0, 2, v)], [], [clip("audio", 1, 1, 5, m)])
    client.post(f"{R}/render", headers=auth_headers, json={})
    job = wait_render(client, auth_headers)
    assert job["status"] == "done", job
    out = ws / job["result"]["rel"]
    assert abs(float(probe(out)["format"]["duration"]) - 5) < 0.25          # Musik endet bei 5 s, Bild nur bis 2 s
    assert abs(job["result"]["duration"] - 5) < 0.01
    assert max_volume(out, 0, 0.9) < -60                                    # vor der Musik: Stille (Video ohne Ton)
    assert max_volume(out, 2.5, 2) > -30                                    # Musik hörbar, auch über dem schwarzen Rest


@needs_ffmpeg
def test_render_only_sound_gives_black_film_with_sound(client, auth_headers, ws) -> None:
    m = make_audio(ws, "satz.wav", 3, freq=440)
    put_tracks(client, auth_headers, [], [clip("audio", 0.5, 0, 2, m)], [])
    assert client.post(f"{R}/render", headers=auth_headers, json={}).status_code == 202
    job = wait_render(client, auth_headers)
    assert job["status"] == "done", job
    out = ws / job["result"]["rel"]
    kinds = sorted(s["codec_type"] for s in probe(out)["streams"])
    assert kinds == ["audio", "video"] and abs(float(probe(out)["format"]["duration"]) - 2.5) < 0.25
    assert max_volume(out, 1, 1) > -30


@needs_ffmpeg
def test_original_sound_and_music_together(client, auth_headers, ws) -> None:
    v = make_video(ws, "laut.mp4", 3)
    b = make_image(ws, "b.png")
    m = make_audio(ws, "lied.wav", 2)
    put_tracks(client, auth_headers, [clip("video", 0, 0, 3, v), clip("image", 3, 0, 2, b)], [], [clip("audio", 3, 0, 2, m)])
    client.post(f"{R}/render", headers=auth_headers, json={})
    job = wait_render(client, auth_headers)
    out = ws / job["result"]["rel"]
    assert job["status"] == "done" and abs(float(probe(out)["format"]["duration"]) - 5) < 0.25
    assert max_volume(out, 0.5, 2) > -30 and max_volume(out, 3.2, 1.5) > -30   # O-Ton, dann Musik unter dem Standbild


@needs_ffmpeg
def test_deleted_music_renders_silence(client, auth_headers, ws) -> None:
    b = make_image(ws, "b.png")
    m = make_audio(ws, "lied.wav", 2)
    put_tracks(client, auth_headers, [clip("image", 0, 0, 2, b)], [], [clip("audio", 0, 0, 2, m)])
    (ws / m).unlink()
    client.post(f"{R}/render", headers=auth_headers, json={})
    job = wait_render(client, auth_headers)
    assert job["status"] == "done", job
    assert max_volume(ws / job["result"]["rel"], 0, 2) < -60


def test_only_deleted_sound_counts_as_empty(client, auth_headers, ws) -> None:
    from _render_helpers import put_tracks as _pt
    from _timeline_helpers import _aclip, _audio, _code
    m = _audio(ws, "lied.mp3")
    _pt(client, auth_headers, [], [], [_aclip(media_rel=m)])
    (ws / m).unlink()
    assert _code(client.post(f"{R}/render", headers=auth_headers, json={})) == "400 studio_render_empty"


@needs_ffmpeg
def test_deleted_sound_counts_as_missing(client, auth_headers, ws) -> None:
    b = make_image(ws, "b.png")
    m = make_audio(ws, "lied.wav", 1)
    put_tracks(client, auth_headers, [clip("image", 0, 0, 2, b)], [clip("audio", 0, 0, 1, m)], [])
    (ws / m).unlink()
    client.post(f"{R}/render", headers=auth_headers, json={})
    assert wait_render(client, auth_headers)["result"]["missing"] == 1
