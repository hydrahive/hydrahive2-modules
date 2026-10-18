"""Studio 6b: Untertitel aus dem Ton heraushören (Spec „Bauplan 6b“). Anbieter ersetzt; der Ton wird echt gemischt."""
from __future__ import annotations

import json

from _hear_helpers import FakeHear, H, wait_hear
from _render_helpers import (
    clip,
    make_audio,
    make_video,
    needs_ffmpeg,
    probe,
    put_tracks,
)
from _subtitle_helpers import P, S, cue, put
from _timeline_helpers import _code

pytest_plugins = ["_hear_helpers"]                 # Fixture `hear`


def _film(client, h, ws):
    v = make_video(ws, "v.mp4", 2)                                    # Video mit Ton (Sinus)
    a = make_audio(ws, "sprache.wav", 1.5, sub="studio/media/voice")
    m = make_audio(ws, "musik.wav", 4, freq=220)
    put_tracks(client, h, [clip("video", 0, 0, 2, v)], [{**clip("audio", 2.5, 0, 1.5, a), "kind": "audio"}],
               [{**clip("audio", 0, 0, 4, m), "kind": "audio"}])


@needs_ffmpeg
def test_hears_original_sound_and_voice_and_makes_subtitles(client, auth_headers, ws, hear) -> None:
    _film(client, auth_headers, ws)
    client.put(f"{P}/screenplay", headers=auth_headers, json={"language": "de"})
    r = client.post(H, headers=auth_headers, json={})
    assert r.status_code == 202, r.text
    assert r.json()["kind"] == "transcribe"
    job = wait_hear(client, auth_headers)
    assert job["status"] == "done", job
    call = hear.calls[0]
    assert call["language"] == "de" and call["model"] == "openai/whisper-large-v3" and call["suffix"] == ".m4a" and call["size"] > 1000
    subs = client.get(f"{S}/de", headers=auth_headers).json()
    assert subs["source"] == "audio" and subs["revision"] == 1
    assert [(c["start"], c["end"], c["text"]) for c in subs["cues"]] == [(0.3, 1.6, "Da ist er endlich."), (1.9, 3.4, "Der alte Ole kommt nach Hause.")]
    assert job["result"] == {"count": 2, "seconds": 4.0, "model": "openai/whisper-large-v3"}
    assert not list((ws / "studio").rglob("*.m4a"))                   # Hördatei wird weggeräumt


@needs_ffmpeg
def test_the_heard_mix_has_no_music(client, auth_headers, ws, monkeypatch) -> None:
    """Die Hördatei enthält Originalton + Sprache, aber nicht die Musik (Tiefpass/Hochpass trennen 220 Hz vom Rest)."""
    from _render_helpers import max_volume
    _film(client, auth_headers, ws)
    kept = {}

    def grab(path, language, model):
        import shutil
        kept["file"] = shutil.copy(path, ws / "gehoert.m4a")
        return [{"start": 0, "end": 1, "text": "x", "no_speech_prob": 0}]
    monkeypatch.setattr("backend.hear_provider.transcribe", grab)
    monkeypatch.setattr("backend.hear_provider.server_model", lambda: "m")
    client.post(H, headers=auth_headers, json={})
    assert wait_hear(client, auth_headers)["status"] == "done"
    f = ws / "gehoert.m4a"
    info = probe(f)
    a = next(s for s in info["streams"] if s["codec_type"] == "audio")
    assert a["codec_name"] == "aac" and abs(float(info["format"]["duration"]) - 4.0) < 0.2
    assert max_volume(f, 0.2, 1.5, af="highpass=f=400") > -30            # Originalton (440 Hz) ist da
    assert max_volume(f, 2.6, 1.2, af="highpass=f=600") > -30            # Sprache (880 Hz) ist da
    assert max_volume(f, 2.05, 0.4, af="lowpass=f=300") < -40            # Musik (220 Hz) fehlt in der Lücke


def test_rules_before_start(client, auth_headers, ws, hear) -> None:
    """Ohne Video/Sprache auf der Zeitleiste gibt es nichts zu hören (Musik allein zählt nicht, siehe test_only_music)."""
    assert _code(client.post(H, headers=auth_headers, json={})) == "400 studio_subtitles_no_audio"
    from _timeline_helpers import _clip, _put
    _put(client, auth_headers, [_clip(kind="placeholder", out=3)])          # nur Platzhalter: nichts zu hören
    assert _code(client.post(H, headers=auth_headers, json={})) == "400 studio_subtitles_no_audio"
    assert _code(client.post(f"{S}/xx/from-audio", headers=auth_headers, json={})) == "404 studio_not_found"
    assert hear.calls == []


@needs_ffmpeg
def test_only_music_counts_as_nothing_to_hear(client, auth_headers, ws, hear) -> None:
    m = make_audio(ws, "musik.wav", 3, freq=220)
    put_tracks(client, auth_headers, [], [], [{**clip("audio", 0, 0, 3, m), "kind": "audio"}])
    assert _code(client.post(H, headers=auth_headers, json={})) == "400 studio_subtitles_no_audio"


@needs_ffmpeg
def test_local_model_is_refused(client, auth_headers, ws, monkeypatch) -> None:
    _film(client, auth_headers, ws)
    monkeypatch.setattr("backend.hear_provider.server_model", lambda: "local/whisper")
    assert _code(client.post(H, headers=auth_headers, json={})) == "400 studio_subtitles_cloud_model"


@needs_ffmpeg
def test_too_long(client, auth_headers, ws, hear) -> None:
    v = make_video(ws, "v.mp4", 1)
    put_tracks(client, auth_headers, [clip("video", 0, 0, 1, v), clip("placeholder", 1, 0, 3600)], [], [])
    assert _code(client.post(H, headers=auth_headers, json={})) == "400 studio_subtitles_too_long"


@needs_ffmpeg
def test_existing_subtitles_need_replace_and_are_not_overwritten_when_changed(client, auth_headers, ws, monkeypatch) -> None:
    import threading
    _film(client, auth_headers, ws)
    put(client, auth_headers, [cue(1, 0, 1, "Von Hand")])
    assert _code(client.post(H, headers=auth_headers, json={})) == "409 studio_subtitles_not_empty"
    gate = threading.Event()

    def slow(path, language, model):
        gate.wait(5)
        return [{"start": 0, "end": 1, "text": "Neu", "no_speech_prob": 0}]
    monkeypatch.setattr("backend.hear_provider.transcribe", slow)
    monkeypatch.setattr("backend.hear_provider.server_model", lambda: "m")
    assert client.post(H, headers=auth_headers, json={"replace": True}).status_code == 202
    assert _code(client.post(H, headers=auth_headers, json={"replace": True})) == "409 studio_subtitles_running"
    put(client, auth_headers, [cue(1, 0, 2, "Inzwischen geändert")], revision=1)      # während des Auftrags
    gate.set()
    job = wait_hear(client, auth_headers)
    assert (job["status"], job["error"]) == ("failed", "changed")
    assert client.get(f"{S}/de", headers=auth_headers).json()["cues"][0]["text"] == "Inzwischen geändert"


@needs_ffmpeg
def test_replace_works(client, auth_headers, ws, hear) -> None:
    _film(client, auth_headers, ws)
    put(client, auth_headers, [cue(1, 0, 1, "Von Hand")])
    client.post(H, headers=auth_headers, json={"replace": True})
    assert wait_hear(client, auth_headers)["status"] == "done"
    subs = client.get(f"{S}/de", headers=auth_headers).json()
    assert subs["revision"] == 2 and subs["cues"][0]["text"] == "Da ist er endlich."
    assert _code(client.post(H, headers=auth_headers, json={"replace": "ja"})) == "409 studio_subtitles_not_empty"


@needs_ffmpeg
def test_provider_errors(client, auth_headers, ws, monkeypatch) -> None:
    _film(client, auth_headers, ws)
    monkeypatch.setattr("backend.hear_provider.server_model", lambda: "m")
    for err in ("no_key", "provider_rejected", "provider_unreachable", "empty_answer"):
        monkeypatch.setattr("backend.hear_provider.transcribe", FakeHear(error=err))
        client.post(H, headers=auth_headers, json={})
        job = wait_hear(client, auth_headers)
        assert (job["status"], job["error"]) == ("failed", err)
    monkeypatch.setattr("backend.hear_provider.transcribe", FakeHear(segments=[{"start": 0, "end": 2, "text": " ", "no_speech_prob": 0},
                                                                              {"start": 2, "end": 3, "text": "Musik", "no_speech_prob": 0.9}]))
    client.post(H, headers=auth_headers, json={})
    job = wait_hear(client, auth_headers)
    assert (job["status"], job["error"]) == ("failed", "no_speech_found")
    assert not (ws / "studio/subtitles/de.json").exists()


def test_only_members(client, other_headers) -> None:
    assert client.post(H, headers=other_headers, json={}).status_code == 404
    assert client.get(f"{S}/de/from-audio", headers=other_headers).status_code in (404, 405)


def test_cue_making_from_segments() -> None:
    from backend.subtitle_hear import cues_from
    segs = [
        {"start": 0, "end": 0.2, "text": " Ja.", "no_speech_prob": 0},                # zu kurz → auf 0,5 s
        {"start": 0.4, "end": 2, "text": " Nein, das stimmt nicht.", "no_speech_prob": 0.1},   # überlappt → beginnt später
        {"start": 3, "end": 4, "text": " [Musik]", "no_speech_prob": 0.7},           # keine Sprache
        {"start": 5, "end": 25, "text": " Ole steht am Ende des alten Holzstegs und schaut lange auf das graue Wasser hinaus. "
                                         "Hinter ihm kreisen die Möwen.", "no_speech_prob": 0},
        {"start": 30, "end": 40, "text": " Ende.", "no_speech_prob": 0},             # hinter dem Film → gekappt
        {"start": "x", "end": 1, "text": "kaputt"}, "kaputt",
    ]
    cues = cues_from(segs, film_end=32)
    texts = [c["text"] for c in cues]
    assert texts[0] == "Ja." and (cues[0]["start"], cues[0]["end"]) == (0, 0.5)
    assert texts[1] == "Nein, das stimmt nicht." and cues[1]["start"] == 0.5
    assert "[Musik]" not in " ".join(texts)
    long = [c for c in cues if 5 <= c["start"] < 25]
    assert len(long) >= 2 and all(c["end"] - c["start"] <= 7 + 1e-6 for c in long)
    assert all(len(line) <= 42 for c in cues for line in c["text"].split("\n"))
    assert cues[-1]["text"] == "Ende." and cues[-1]["end"] == 32
    from itertools import pairwise
    assert all(b["start"] >= a["end"] - 1e-9 for a, b in pairwise(cues))


def test_real_provider_sends_language_and_reads_segments(monkeypatch, tmp_path) -> None:
    import httpx
    import hydrahive.llm._config as cfg
    import pytest

    from backend import hear_provider
    f = tmp_path / "a.m4a"
    f.write_bytes(b"\0" * 2000)
    seen = {}

    def handler(req):
        seen["body"] = req.read()
        return httpx.Response(200, json={"text": "Hallo", "segments": [{"start": 0.5, "end": 1.2, "text": " Hallo", "no_speech_prob": 0.01, "x": 1}]})
    real = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda **kw: real(transport=httpx.MockTransport(handler), **kw))
    monkeypatch.setattr(cfg, "openrouter_key", lambda: "k")
    assert hear_provider.transcribe(f, "de", "openai/whisper-large-v3") == [{"start": 0.5, "end": 1.2, "text": " Hallo", "no_speech_prob": 0.01}]
    body = seen["body"]
    for part in (b'name="language"\r\n\r\nde', b'name="response_format"\r\n\r\nverbose_json', b'name="model"\r\n\r\nopenai/whisper-large-v3',
                 b'name="timestamp_granularities[]"\r\n\r\nsegment'):
        assert part in body, part
    for status, code in ((402, "provider_rejected"), (500, "provider_rejected")):
        monkeypatch.setattr(httpx, "Client", lambda s=status, **kw: real(transport=httpx.MockTransport(lambda r: httpx.Response(s, text="x")), **kw))
        with pytest.raises(hear_provider.ProviderError) as e:
            hear_provider.transcribe(f, "de", "m")
        assert str(e.value) == code
    monkeypatch.setattr(httpx, "Client", lambda **kw: real(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"text": "x"})), **kw))
    with pytest.raises(hear_provider.ProviderError) as e:
        hear_provider.transcribe(f, "de", "m")
    assert str(e.value) == "empty_answer"                                 # ohne Abschnitte keine Zeiten

    def down(r):
        raise httpx.ConnectError("weg")
    monkeypatch.setattr(httpx, "Client", lambda **kw: real(transport=httpx.MockTransport(down), **kw))
    with pytest.raises(hear_provider.ProviderError) as e:
        hear_provider.transcribe(f, "de", "m")
    assert str(e.value) == "provider_unreachable"
    monkeypatch.setattr(cfg, "openrouter_key", lambda: "")
    with pytest.raises(hear_provider.ProviderError) as e:
        hear_provider.transcribe(f, "de", "m")
    assert str(e.value) == "no_key"


def test_defaults_for_the_dialog(client, auth_headers, ws, hear) -> None:
    from _timeline_helpers import _clip, _put
    _put(client, auth_headers, [_clip(kind="placeholder", out=90)])
    d = client.get(f"{S}/de/from-audio", headers=auth_headers).json()
    assert d == {"seconds": 90, "model": "openai/whisper-large-v3", "cloud": True, "existing": 0, "max_seconds": 3600}
    put(client, auth_headers, [cue(1, 0, 1)])
    assert client.get(f"{S}/de/from-audio", headers=auth_headers).json()["existing"] == 1
    assert json.dumps(d)                                                  # einfache Werte
    assert _code(client.get(f"{S}/xx/from-audio", headers=auth_headers)) == "404 studio_not_found"
