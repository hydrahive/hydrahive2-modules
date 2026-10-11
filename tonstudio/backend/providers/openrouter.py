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
import logging

import httpx

from hydrahive.tools._openrouter_media import openrouter_key

from ..prompt import MusicRequest, build_prompt
from ._base import MusicModel, MusicResult, ProviderError
from ._sse import StreamResult, read_stream

logger = logging.getLogger(__name__)

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
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                async with client.stream("POST", _URL, json=payload,
                                         headers={"Authorization": f"Bearer {key}",
                                                  "Content-Type": "application/json"}) as resp:
                    if resp.status_code >= 400:
                        body = (await resp.aread()).decode("utf-8", "replace")[:300]
                        logger.warning("tonstudio openrouter %s HTTP %s: %s", model_id, resp.status_code, body)
                        raise ProviderError(f"OpenRouter antwortete {resp.status_code}: {body}")
                    res = await read_stream(resp)
        except httpx.HTTPError as e:
            logger.warning("tonstudio openrouter %s Netzwerkfehler: %s", model_id, type(e).__name__)
            raise ProviderError(f"Netzwerkfehler bei OpenRouter: {type(e).__name__}") from e
        return _finish(model_id, prompt, res)


def _finish(model_id: str, prompt: str, res: StreamResult) -> MusicResult:
    """Stream-Ergebnis prüfen. Jeder Fehlschlag wird mit Generierungs-ID protokolliert (nachvollziehbar bei
    OpenRouter) und nennt in der Meldung, was statt Audio kam."""
    info = res.summary()
    if res.errors:
        logger.warning("tonstudio openrouter %s Fehler im Stream (%s): %s", model_id, info, res.errors)
        raise ProviderError(f"OpenRouter meldet einen Fehler: {'; '.join(res.errors)[:300]} ({info})")
    if not res.audio:
        logger.warning("tonstudio openrouter %s ohne Audio (%s), Text: %r", model_id, info, res.text_head())
        raise ProviderError(f"Keine Audio-Daten erhalten – bitte noch einmal versuchen. ({info})")
    if not res.done:
        logger.warning("tonstudio openrouter %s Stream abgebrochen (%s)", model_id, info)
        raise ProviderError(f"Antwort vorzeitig abgebrochen – bitte noch einmal versuchen. ({info})")
    try:
        raw = base64.b64decode("".join(res.audio), validate=True)
    except (ValueError, binascii.Error) as e:
        logger.warning("tonstudio openrouter %s Audio nicht lesbar (%s)", model_id, info)
        raise ProviderError(f"Audio-Daten nicht lesbar. ({info})") from e
    logger.info("tonstudio openrouter %s ok (%s), %d Bytes", model_id, info, len(raw))
    return MusicResult(audio=raw, ext="mp3", text="".join(res.text).strip(), prompt=prompt)
