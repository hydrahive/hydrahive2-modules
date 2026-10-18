"""Studio 5a: Wellenform eines Tonclips (studio/SPEC.md „Bauplan Etappe 5“): einmal rechnen, im Cache ablegen."""
from __future__ import annotations

from _render_helpers import R, make_audio, make_video, needs_ffmpeg
from _timeline_helpers import _audio, _code
from conftest import MOD_PREFIX, OTHER_PROJECT_ID

W = f"{R}/waveform"


@needs_ffmpeg
def test_waveform_of_a_real_file_is_cached(client, auth_headers, ws) -> None:
    m = make_audio(ws, "lied.wav", 2)
    r = client.get(W, headers=auth_headers, params={"rel": m})
    assert r.status_code == 200, r.text
    w = r.json()
    assert w["per_second"] == 50 and abs(w["duration"] - 2) < 0.05
    assert abs(len(w["peaks"]) - 100) <= 1 and all(0 <= p <= 100 for p in w["peaks"])
    assert 10 <= max(w["peaks"]) <= 15                                     # lavfi-Sinus hat 1/8 Lautstärke (−18 dB) → 12
    cached = list((ws / "studio/cache/peaks").glob("*.json"))
    assert len(cached) == 1
    cached[0].write_text('{"per_second": 50, "duration": 2, "peaks": [7]}')   # zweiter Abruf kommt aus dem Cache
    assert client.get(W, headers=auth_headers, params={"rel": m}).json()["peaks"] == [7]
    make_audio(ws, "lied.wav", 1)                                            # Datei geändert → neu rechnen
    assert len(client.get(W, headers=auth_headers, params={"rel": m}).json()["peaks"]) in (49, 50, 51)


@needs_ffmpeg
def test_waveform_of_video_sound(client, auth_headers, ws) -> None:
    v = make_video(ws, "a.mp4", 1)
    w = client.get(W, headers=auth_headers, params={"rel": v}).json()
    assert 49 <= len(w["peaks"]) <= 53 and max(w["peaks"]) > 5             # AAC bringt ein paar Füll-Samples mit


def test_unreadable_file_gives_flat_line_without_cache(client, auth_headers, ws) -> None:
    m = _audio(ws, "kaputt.mp3")                                            # nur ein Kopf, kein Ton
    r = client.get(W, headers=auth_headers, params={"rel": m})
    assert r.status_code == 200 and r.json()["peaks"] == []
    assert not list((ws / "studio/cache/peaks").glob("*.json")) if (ws / "studio/cache/peaks").exists() else True


def test_waveform_only_for_media_in_the_project(client, auth_headers, other_headers, ws) -> None:
    _audio(ws, "lied.mp3")
    for rel in ("../x.mp3", "/etc/passwd", "atelier/audio/weg.mp3", "studio/timelines/main.json", ""):
        assert _code(client.get(W, headers=auth_headers, params={"rel": rel})) == "404 studio_media_not_found", rel
    assert client.get(W, headers=other_headers, params={"rel": "atelier/audio/lied.mp3"}).status_code == 404
    assert client.get(f"{MOD_PREFIX}/projects/{OTHER_PROJECT_ID}/waveform", headers=auth_headers,
                      params={"rel": "atelier/audio/lied.mp3"}).status_code == 404


def test_peaks_from_pcm_is_pure() -> None:
    from array import array

    from backend import waveform as wf
    step = wf.RATE // wf.PER_SECOND
    pcm = array("h", [0] * step + [16384, -32768] + [0] * (step - 2) + [100] * 3).tobytes()
    assert wf.peaks_from_pcm(pcm) == [0, 100, 0]                          # Betrag, auf 0–100 gerundet; Rest = eigener Wert
    assert wf.peaks_from_pcm(b"") == [] and wf.peaks_from_pcm(b"\x01") == []
