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
