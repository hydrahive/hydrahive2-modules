"""Musik über OpenRouter (Lyria). Entscheidung Till 11.10.: externe Anbieter nur über OpenRouter.

- Modelle live aus ``/api/v1/models`` (Kern: ``list_audio_models``, Ausgabe ``audio``). Sprach-Modelle (gpt-audio)
  sind keine Musik und werden ausgefiltert. Unbekannte Musik-Modelle erscheinen automatisch, aber ohne behauptete
  Fähigkeiten (SPEC §5.6).
- Aufruf wie ``hydrahive.tools.generate_music``: Chat-Completions mit ``modalities: [text, audio]``, SSE-Stream.
  Lyria liefert Audio als EINE mehrere MB große Zeile; deshalb Bytes selbst an ``\\n`` trennen (wie
  ``read_audio_sse`` im Kern). Zusätzlich wird ``delta.content`` gesammelt – der Kern-Parser verwirft ihn, das
  Tonstudio braucht ihn für den zurückgelieferten Liedtext (M3).
"""
from __future__ import annotations

import base64
import binascii
import json

import httpx

from hydrahive.tools._openrouter_media import openrouter_key

from ..prompt import MusicRequest, build_prompt
from ._base import MusicModel, MusicResult, ProviderError

_URL = "https://openrouter.ai/api/v1/chat/completions"
_TIMEOUT = 300.0
_NOT_MUSIC = ("openai/gpt-audio",)          # Sprach-Ausgabe, keine Musik

# Bekannte Fähigkeiten (Quellen: OpenRouter /models input text+image; Google Lyria-Doku; Stand 11.10.2026).
_KNOWN: dict[str, dict] = {
    "google/lyria-3-pro-preview": dict(lyrics=True, image_ref=True, max_seconds=180,
                                       notes=["ganze Stücke, ca. 2:30–3:00 (gemessen Juni 2026)"]),
    "google/lyria-3-clip-preview": dict(lyrics=True, image_ref=True, max_seconds=30,
                                        notes=["kurze Clips, immer ca. 30 s"]),
}
_PRICE_NOTE = "Kosten unbekannt – OpenRouter meldet 0 (geprüft 11.10.2026)"


async def _live_audio_models() -> list[dict]:
    from hydrahive.llm.media_models import list_audio_models
    return await list_audio_models()


def _model(entry: dict) -> MusicModel:
    mid = entry["id"]
    known = _KNOWN.get(mid, {})
    return MusicModel(id=mid, name=entry.get("name") or mid, backend="openrouter", price_note=_PRICE_NOTE,
                      license_note="Bedingungen des Modell-Anbieters (über OpenRouter)", **known)


def _parse_line(line: str, audio: list[str], text: list[str]) -> bool:
    """Eine SSE-Zeile auswerten. True bei ``[DONE]``."""
    if not line.startswith("data:"):
        return False
    payload = line[5:].strip()
    if payload == "[DONE]":
        return True
    try:
        delta = (json.loads(payload).get("choices") or [{}])[0].get("delta") or {}
    except (ValueError, AttributeError):
        return False
    if isinstance(delta.get("audio"), dict) and delta["audio"].get("data"):
        audio.append(delta["audio"]["data"])
    if isinstance(delta.get("content"), str):
        text.append(delta["content"])
    return False


class OpenRouterBackend:
    name = "openrouter"

    async def list_models(self) -> list[MusicModel]:
        try:
            live = await _live_audio_models()
        except Exception:                       # noqa: BLE001 – ohne Netz: bekannte Modelle trotzdem zeigen
            live = [{"id": k, "name": k} for k in _KNOWN]
        return [_model(e) for e in live if e.get("id") and not e["id"].startswith(_NOT_MUSIC)]

    async def generate(self, model_id: str, req: MusicRequest) -> MusicResult:
        key = openrouter_key()
        if not key:
            raise ProviderError("Kein OpenRouter-Schlüssel eingerichtet (Einstellungen → KI-Modelle).")
        prompt = build_prompt(req)
        payload = {"model": model_id, "messages": [{"role": "user", "content": prompt}],
                   "modalities": ["text", "audio"], "audio": {"format": "mp3"}, "stream": True}
        audio: list[str] = []
        text: list[str] = []
        done = False
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                async with client.stream("POST", _URL, json=payload,
                                         headers={"Authorization": f"Bearer {key}",
                                                  "Content-Type": "application/json"}) as resp:
                    if resp.status_code >= 400:
                        body = (await resp.aread()).decode("utf-8", "replace")[:300]
                        raise ProviderError(f"OpenRouter antwortete {resp.status_code}: {body}")
                    buf = b""
                    async for chunk in resp.aiter_bytes():
                        buf += chunk
                        while b"\n" in buf:
                            line, buf = buf.split(b"\n", 1)
                            done = _parse_line(line.decode("utf-8", "replace").rstrip("\r"), audio, text) or done
                    if buf:
                        done = _parse_line(buf.decode("utf-8", "replace"), audio, text) or done
        except httpx.HTTPError as e:
            raise ProviderError(f"Netzwerkfehler bei OpenRouter: {type(e).__name__}") from e
        if not audio:
            raise ProviderError("Keine Audio-Daten erhalten – bitte noch einmal versuchen.")
        if not done:
            raise ProviderError("Antwort vorzeitig abgebrochen – bitte noch einmal versuchen.")
        try:
            raw = base64.b64decode("".join(audio), validate=True)
        except (ValueError, binascii.Error) as e:
            raise ProviderError("Audio-Daten nicht lesbar.") from e
        return MusicResult(audio=raw, ext="mp3", text="".join(text).strip(), prompt=prompt)
