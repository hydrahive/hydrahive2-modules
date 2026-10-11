"""Prompt-Bau und Musik-Anbieter (SPEC.md §5.6). HTTP wird nie echt aufgerufen."""
from __future__ import annotations

import asyncio
import base64

import pytest


# ── Prompt ─────────────────────────────────────────────────────────────────────

def test_prompt_enthaelt_alle_angaben_in_fester_reihenfolge():
    from backend.prompt import MusicRequest, build_prompt
    req = MusicRequest(style="Epic Celtic trance, uilleann pipes", description="raue grüne Landschaft im Morgengrauen",
                       bpm=132, key="D minor", duration_s=150, instrumental=True)
    p = build_prompt(req)
    assert p.index("Epic Celtic trance") < p.index("raue grüne Landschaft") < p.index("132 BPM")
    assert "in D minor" in p and "about 2:30" in p and "Instrumental only" in p


def test_prompt_ohne_optionale_angaben():
    from backend.prompt import MusicRequest, build_prompt
    p = build_prompt(MusicRequest(description="ein ruhiges Klavierstück"))
    assert p == "ein ruhiges Klavierstück"


def test_prompt_mit_liedtext_nutzt_lyrics_kopf():
    """Lyria-Prompt-Guide: eigener Text unter 'Lyrics:' mit Abschnitt-Markern."""
    from backend.prompt import MusicRequest, build_prompt
    p = build_prompt(MusicRequest(description="folk song", lyrics="[Verse 1]\nEs war einmal\n[Chorus]\nLa la"))
    assert p.endswith("Lyrics:\n[Verse 1]\nEs war einmal\n[Chorus]\nLa la")
    assert "Instrumental only" not in p


def test_instrumental_und_liedtext_widersprechen_sich():
    from backend.prompt import MusicRequest
    with pytest.raises(ValueError):
        MusicRequest(description="x", lyrics="[Chorus]\nla", instrumental=True)


def test_leerer_auftrag_wird_abgelehnt():
    from backend.prompt import MusicRequest
    with pytest.raises(ValueError):
        MusicRequest()


# ── Registry ───────────────────────────────────────────────────────────────────

def test_lyria_modelle_melden_ihre_faehigkeiten(monkeypatch):
    from backend import providers
    from backend.providers import openrouter
    monkeypatch.setattr(openrouter, "_live_audio_models", _fake_live)
    models = {m.id: m for m in asyncio.run(providers.list_models())}
    pro = models["google/lyria-3-pro-preview"]
    assert pro.backend == "openrouter" and pro.lyrics and pro.image_ref and not pro.audio_ref
    assert pro.max_seconds >= 120 and not pro.local
    assert models["google/lyria-3-clip-preview"].max_seconds == 30


def test_unbekannte_audio_modelle_von_openrouter_werden_vorsichtig_gemeldet(monkeypatch):
    """Neue OpenRouter-Musikmodelle erscheinen automatisch, aber ohne behauptete Fähigkeiten (§5.6)."""
    from backend import providers
    from backend.providers import openrouter

    async def live():
        return [{"id": "acme/neue-musik", "name": "Acme Musik"}]
    monkeypatch.setattr(openrouter, "_live_audio_models", live)
    m = {x.id: x for x in asyncio.run(providers.list_models())}["acme/neue-musik"]
    assert m.lyrics is False and m.image_ref is False and m.audio_ref is False and m.max_seconds is None


def test_sprach_modelle_erscheinen_nicht_als_musik(monkeypatch):
    from backend import providers
    from backend.providers import openrouter

    async def live():
        return [{"id": "openai/gpt-audio", "name": "GPT Audio"}, {"id": "google/lyria-3-pro-preview", "name": "Lyria"}]
    monkeypatch.setattr(openrouter, "_live_audio_models", live)
    ids = [m.id for m in asyncio.run(providers.list_models())]
    assert "openai/gpt-audio" not in ids and "google/lyria-3-pro-preview" in ids


def test_get_findet_modell_nach_id(monkeypatch):
    from backend import providers
    from backend.providers import openrouter
    monkeypatch.setattr(openrouter, "_live_audio_models", _fake_live)
    model, backend = asyncio.run(providers.resolve("google/lyria-3-clip-preview"))
    assert model.id == "google/lyria-3-clip-preview" and backend.name == "openrouter"
    with pytest.raises(providers.UnknownModel):
        asyncio.run(providers.resolve("gibt/es-nicht"))


async def _fake_live():
    return [{"id": "google/lyria-3-pro-preview", "name": "Lyria 3 Pro"},
            {"id": "google/lyria-3-clip-preview", "name": "Lyria 3 Clip"}]


# ── OpenRouter-Aufruf ──────────────────────────────────────────────────────────

MP3 = b"ID3\x04fake-mp3-bytes"


def _sse(audio_parts: list[str], *, done: bool = True, text: str = "") -> bytes:
    lines = []
    if text:
        lines.append('data: {"choices":[{"delta":{"content":' + _j(text) + '}}]}')
    for p in audio_parts:
        lines.append('data: {"choices":[{"delta":{"audio":{"data":"' + p + '"}}}]}')
    if done:
        lines.append("data: [DONE]")
    return ("\n\n".join(lines) + "\n\n").encode()


def _j(s: str) -> str:
    import json
    return json.dumps(s)


class _FakeResp:
    def __init__(self, status: int, body: bytes):
        self.status_code, self._body = status, body

    async def aread(self) -> bytes:
        return self._body

    async def aiter_raw(self):
        for i in range(0, len(self._body), 7):           # absichtlich klein zerstückelt
            yield self._body[i:i + 7]

    async def aiter_bytes(self):
        async for c in self.aiter_raw():
            yield c


class _FakeStream:
    def __init__(self, resp, seen):
        self.resp, self.seen = resp, seen

    async def __aenter__(self):
        return self.resp

    async def __aexit__(self, *a):
        return False


class _FakeClient:
    def __init__(self, resp, seen):
        self.resp, self.seen = resp, seen

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    def stream(self, method, url, headers=None, json=None):
        self.seen.update(method=method, url=url, headers=headers, json=json)
        return _FakeStream(self.resp, self.seen)


@pytest.fixture
def fake_http(monkeypatch):
    from backend.providers import openrouter
    state: dict = {}

    def install(status=200, body=b""):
        resp = _FakeResp(status, body)
        monkeypatch.setattr(openrouter.httpx, "AsyncClient", lambda **kw: _FakeClient(resp, state))
        monkeypatch.setattr(openrouter, "openrouter_key", lambda: "sk-test")
        return state
    return install


def _req(**kw):
    from backend.prompt import MusicRequest
    return MusicRequest(**({"description": "ruhiges Klavier"} | kw))


def test_erfolg_liefert_mp3_und_text(fake_http):
    from backend.providers.openrouter import OpenRouterBackend
    b64 = base64.b64encode(MP3).decode()
    seen = fake_http(body=_sse([b64[:10], b64[10:]], text="[Verse 1]\nla la"))
    res = asyncio.run(OpenRouterBackend().generate("google/lyria-3-pro-preview", _req()))
    assert res.audio == MP3 and res.ext == "mp3"
    assert seen["json"]["model"] == "google/lyria-3-pro-preview"
    assert seen["json"]["modalities"] == ["text", "audio"] and seen["json"]["stream"] is True
    assert seen["json"]["messages"][0]["content"] == "ruhiges Klavier"
    assert seen["headers"]["Authorization"] == "Bearer sk-test"


def test_ohne_schluessel_klarer_fehler(monkeypatch):
    from backend.providers import openrouter
    monkeypatch.setattr(openrouter, "openrouter_key", lambda: "")
    with pytest.raises(openrouter.ProviderError, match="OpenRouter"):
        asyncio.run(openrouter.OpenRouterBackend().generate("google/lyria-3-pro-preview", _req()))


def test_http_fehler_wird_weitergereicht_ohne_schluessel(fake_http):
    from backend.providers.openrouter import OpenRouterBackend, ProviderError
    fake_http(status=402, body=b'{"error":"insufficient credits"}')
    with pytest.raises(ProviderError) as e:
        asyncio.run(OpenRouterBackend().generate("google/lyria-3-pro-preview", _req()))
    assert "402" in str(e.value) and "sk-test" not in str(e.value)


def test_leerer_oder_abgebrochener_stream_ist_fehler(fake_http):
    from backend.providers.openrouter import OpenRouterBackend, ProviderError
    fake_http(body=_sse([]))
    with pytest.raises(ProviderError, match="Keine Audio"):
        asyncio.run(OpenRouterBackend().generate("google/lyria-3-pro-preview", _req()))
    fake_http(body=_sse([base64.b64encode(MP3).decode()], done=False))
    with pytest.raises(ProviderError, match="vorzeitig"):
        asyncio.run(OpenRouterBackend().generate("google/lyria-3-pro-preview", _req()))


def test_text_aus_mehreren_stuecken_wird_zusammengesetzt(fake_http):
    """Lyria liefert Liedtext/Struktur als delta.content – der Kern-Parser verwirft das, wir brauchen es (M3)."""
    from backend.providers.openrouter import OpenRouterBackend
    b64 = base64.b64encode(MP3).decode()
    body = ('data: {"choices":[{"delta":{"content":"[Verse 1]\\n"}}]}\n\n'
            'data: {"choices":[{"delta":{"content":"Es war einmal"}}]}\n\n'
            'data: {"choices":[{"delta":{"audio":{"data":"' + b64 + '"}}}]}\n\n'
            ': keep-alive\n\ndata: [DONE]\n\n').encode()
    fake_http(body=body)
    res = asyncio.run(OpenRouterBackend().generate("google/lyria-3-pro-preview", _req()))
    assert res.text == "[Verse 1]\nEs war einmal" and res.audio == MP3


def test_ohne_netz_bleiben_bekannte_modelle_sichtbar(monkeypatch):
    from backend import providers
    from backend.providers import openrouter

    async def boom():
        raise RuntimeError("kein Netz")
    monkeypatch.setattr(openrouter, "_live_audio_models", boom)
    ids = {m.id for m in asyncio.run(providers.list_models())}
    assert {"google/lyria-3-pro-preview", "google/lyria-3-clip-preview"} <= ids


def test_ohne_audio_meldet_was_stattdessen_kam(fake_http, caplog):
    """Live gesehen (11.10.): Lyria liefert manchmal keinen Track. Die Meldung muss sagen, was kam (Generierungs-ID,
    finish_reason, Text-Anfang), und es wird protokolliert – sonst ist es nicht nachvollziehbar."""
    import logging

    from backend.providers.openrouter import OpenRouterBackend, ProviderError
    body = ('data: {"id":"gen-123abc","choices":[{"delta":{"content":"[[A0]]\\n[:] Die Sonne"}}]}\n\n'
            ': OPENROUTER PROCESSING\n\n'
            'data: {"id":"gen-123abc","choices":[{"delta":{"content":""},"finish_reason":"stop",'
            '"native_finish_reason":"STOP"}]}\n\ndata: [DONE]\n\n').encode()
    fake_http(body=body)
    with caplog.at_level(logging.WARNING), pytest.raises(ProviderError) as e:
        asyncio.run(OpenRouterBackend().generate("google/lyria-3-pro-preview", _req()))
    msg = str(e.value)
    assert "Keine Audio" in msg and "gen-123abc" in msg and "stop" in msg
    assert "gen-123abc" in caplog.text and "Die Sonne" in caplog.text
    assert "sk-test" not in caplog.text


def test_fehler_im_stream_wird_gemeldet(fake_http):
    """OpenRouter meldet Anbieter-Fehler nach dem 200 als SSE-Objekt mit "error" – das muss in der Meldung stehen."""
    from backend.providers.openrouter import OpenRouterBackend, ProviderError
    body = ('data: {"id":"gen-9","error":{"code":502,"message":"Provider returned error"},'
            '"choices":[{"delta":{"content":""},"finish_reason":"error"}]}\n\ndata: [DONE]\n\n').encode()
    fake_http(body=body)
    with pytest.raises(ProviderError) as e:
        asyncio.run(OpenRouterBackend().generate("google/lyria-3-pro-preview", _req()))
    assert "Provider returned error" in str(e.value) and "502" in str(e.value)


def test_erfolg_wird_mit_generierungs_id_protokolliert(fake_http, caplog):
    import logging

    from backend.providers.openrouter import OpenRouterBackend
    b64 = base64.b64encode(MP3).decode()
    body = ('data: {"id":"gen-ok1","choices":[{"delta":{"audio":{"data":"' + b64 + '"}}}]}\n\n'
            'data: [DONE]\n\n').encode()
    fake_http(body=body)
    with caplog.at_level(logging.INFO):
        asyncio.run(OpenRouterBackend().generate("google/lyria-3-pro-preview", _req()))
    assert "gen-ok1" in caplog.text


_LEER_OTHER = ('data: {"id":"gen-leer","choices":[{"delta":{"content":"[[A0]]"},"finish_reason":"stop",'
               '"native_finish_reason":"OTHER"}]}\n\ndata: [DONE]\n\n').encode()


class _Seq:
    """Mehrere Antworten nacheinander (je Aufruf von AsyncClient eine)."""
    def __init__(self, bodies):
        self.bodies, self.calls = list(bodies), 0


def _install_seq(monkeypatch, seq):
    from backend.providers import openrouter

    def make(**kw):
        body = seq.bodies[min(seq.calls, len(seq.bodies) - 1)]
        seq.calls += 1
        return _FakeClient(_FakeResp(200, body), {})
    monkeypatch.setattr(openrouter.httpx, "AsyncClient", make)
    monkeypatch.setattr(openrouter, "openrouter_key", lambda: "sk-test")


def test_leerer_track_mit_other_wird_einmal_wiederholt(monkeypatch):
    """Till 11.10.: Lyria liefert manchmal ohne Grund keinen Track (finish=stop, native=OTHER) → EINMAL selbst
    neu versuchen. Klappt der zweite, ist alles gut."""
    from backend.providers.openrouter import OpenRouterBackend
    b64 = base64.b64encode(MP3).decode()
    ok = ('data: {"id":"gen-ok","choices":[{"delta":{"audio":{"data":"' + b64 + '"}}}]}\n\ndata: [DONE]\n\n').encode()
    seq = _Seq([_LEER_OTHER, ok])
    _install_seq(monkeypatch, seq)
    res = asyncio.run(OpenRouterBackend().generate("google/lyria-3-pro-preview", _req()))
    assert res.audio == MP3 and seq.calls == 2


def test_wiederholung_hoechstens_einmal(monkeypatch):
    from backend.providers.openrouter import OpenRouterBackend, ProviderError
    seq = _Seq([_LEER_OTHER, _LEER_OTHER, _LEER_OTHER])
    _install_seq(monkeypatch, seq)
    with pytest.raises(ProviderError, match="Keine Audio") as e:
        asyncio.run(OpenRouterBackend().generate("google/lyria-3-pro-preview", _req()))
    assert seq.calls == 2 and "2 Versuche" in str(e.value)


def test_gesperrter_prompt_wird_nicht_wiederholt(monkeypatch):
    """Ausdrücklicher Block (error im Stream) ist kein Zufall – nicht wiederholen, das kostet nur."""
    from backend.providers.openrouter import OpenRouterBackend, ProviderError
    block = ('data: {"id":"gen-b","error":{"code":502,"message":"Gemini blocked the response: OTHER"}}\n\n').encode()
    seq = _Seq([block, block])
    _install_seq(monkeypatch, seq)
    with pytest.raises(ProviderError, match="blocked"):
        asyncio.run(OpenRouterBackend().generate("google/lyria-3-pro-preview", _req()))
    assert seq.calls == 1


def test_leer_ohne_other_wird_nicht_wiederholt(monkeypatch):
    """Nur der belegte Fall (native=OTHER) wird wiederholt, kein pauschales Retry."""
    from backend.providers.openrouter import OpenRouterBackend, ProviderError
    seq = _Seq([_sse([]), _sse([])])
    _install_seq(monkeypatch, seq)
    with pytest.raises(ProviderError):
        asyncio.run(OpenRouterBackend().generate("google/lyria-3-pro-preview", _req()))
    assert seq.calls == 1
