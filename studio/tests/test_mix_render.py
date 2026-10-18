"""Studio 5b: Mischpult im echten Film (ffmpeg) – Pegel per volumedetect (studio/SPEC.md „Bauplan 5b“)."""
from __future__ import annotations

from _render_helpers import R, clip, make_audio, make_image, max_volume, needs_ffmpeg, wait_render

T = f"{R}/timeline"


def _put(client, h, video, voice, music, **kw):
    cur = client.get(T, headers=h).json()
    tracks = [{"id": "V1", "kind": "video", "clips": video, **kw.get("V1", {})},
              {"id": "A1", "kind": "audio", "clips": voice, **kw.get("A1", {})},
              {"id": "A2", "kind": "audio", "clips": music, **kw.get("A2", {})}]
    r = client.put(T, headers=h, json={"revision": cur["revision"], "fps": 25, "tracks": tracks, **kw.get("top", {})})
    assert r.status_code == 200, r.text


def _film(client, h, ws):
    client.post(f"{R}/render", headers=h, json={})
    job = wait_render(client, h)
    assert job["status"] == "done", job
    return ws / job["result"]["rel"]


@needs_ffmpeg
def test_gain_mute_and_solo(client, auth_headers, ws) -> None:
    b = make_image(ws, "b.png")
    m = make_audio(ws, "m.wav", 4)
    s = make_audio(ws, "s.wav", 4, freq=440)
    _put(client, auth_headers, [clip("image", 0, 0, 4, b)], [], [clip("audio", 0, 0, 4, m)])
    loud = max_volume(_film(client, auth_headers, ws), 1, 2)
    _put(client, auth_headers, [clip("image", 0, 0, 4, b)], [], [clip("audio", 0, 0, 4, m) | {"gain_db": -20}])
    quiet = max_volume(_film(client, auth_headers, ws), 1, 2)
    assert 17 < loud - quiet < 23                                        # −20 dB messbar
    _put(client, auth_headers, [clip("image", 0, 0, 4, b)], [], [clip("audio", 0, 0, 4, m)], A2={"mute": True})
    assert max_volume(_film(client, auth_headers, ws), 1, 2) < -60
    _put(client, auth_headers, [clip("image", 0, 0, 4, b)], [clip("audio", 0, 0, 4, s)], [clip("audio", 0, 0, 4, m)],
         A2={"solo": True}, top={"duck": False})
    assert max_volume(_film(client, auth_headers, ws), 1, 2) == max_volume(_film(client, auth_headers, ws), 1, 2) > -30   # nur Musik


@needs_ffmpeg
def test_fade_in(client, auth_headers, ws) -> None:
    b = make_image(ws, "b.png")
    m = make_audio(ws, "m.wav", 4)
    _put(client, auth_headers, [clip("image", 0, 0, 4, b)], [], [clip("audio", 0, 0, 4, m) | {"fade_in": 2}])
    f = _film(client, auth_headers, ws)
    assert max_volume(f, 0, 0.3) < max_volume(f, 1.0, 0.3) - 6 < max_volume(f, 2.5, 1) - 6


@needs_ffmpeg
def test_music_ducks_under_voice(client, auth_headers, ws) -> None:
    b = make_image(ws, "b.png")
    m = make_audio(ws, "m.wav", 8, freq=220)
    s = make_audio(ws, "s.wav", 2, freq=1000)
    music, voice = [clip("audio", 0, 0, 8, m)], [clip("audio", 3, 0, 2, s)]
    _put(client, auth_headers, [clip("image", 0, 0, 8, b)], voice, music, A1={"mute": False})
    ducked = _film(client, auth_headers, ws)
    _put(client, auth_headers, [clip("image", 0, 0, 8, b)], voice, music, top={"duck": False})
    plain = _film(client, auth_headers, ws)
    # nur die Musik messen: Ausschnitt mit Sprache über einen Tiefpass unter 600 Hz
    low = lambda f, s0, d: max_volume(f, s0, d, af="lowpass=f=400,lowpass=f=400")   # noqa: E731
    assert low(plain, 3.4, 1.2) - low(ducked, 3.4, 1.2) > 8                 # während Sprache deutlich leiser
    assert abs(low(plain, 0.5, 1.5) - low(ducked, 0.5, 1.5)) < 1.5         # vorher gleich
    assert abs(low(plain, 6.5, 1) - low(ducked, 6.5, 1)) < 1.5             # nachher wieder gleich
