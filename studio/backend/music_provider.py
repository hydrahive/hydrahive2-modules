"""Musik-Anbieter für das Studio (Spec „Nachtrag 5c-2“): OpenRouter-Chat mit `modalities: [text, audio]` als Stream.

Den Stream liest der Kern (`_openrouter_media.read_audio_sse` – das Audio kommt als eine mehrere MB große Zeile).
Aufruf wie im Atelier (atelier/backend/music.py), eigene Fassung, weil das Atelier in Etappe 8 entfällt. Fehler tragen
nur einen Code; den Text für Menschen liefert das Frontend.
"""
from __future__ import annotations

import asyncio
import base64
import binascii
import logging

import httpx

logger = logging.getLogger("hhmod_studio.music")

URL = "https://openrouter.ai/api/v1/chat/completions"
TIMEOUT = 240.0
MAX_BYTES = 40 * 1024 * 1024


class ProviderError(RuntimeError):
    """Fehlercode: no_key, provider_rejected, provider_unreachable, empty_answer."""


def server_default_model() -> str:
    from hydrahive.llm.media_models import get_media_model
    return get_media_model("music")


async def _request(key: str, model: str, prompt: str) -> bytes:
    from hydrahive.tools._openrouter_media import read_audio_sse
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "modalities": ["text", "audio"],
               "audio": {"format": "mp3"}, "stream": True}
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=TIMEOUT) as client, client.stream("POST", URL, json=payload, headers=headers) as resp:
        if resp.status_code >= 400:
            body = (await resp.aread()).decode("utf-8", "replace")[:300]
            logger.info("Studio-Musik: Anbieter lehnt ab (%s, %s): %s", model, resp.status_code, body)
            raise ProviderError("provider_rejected")
        parts, done = await read_audio_sse(resp)
    if not parts or not done:
        raise ProviderError("empty_answer")
    try:
        data = base64.b64decode("".join(parts), validate=True)
    except (ValueError, binascii.Error) as e:
        raise ProviderError("empty_answer") from e
    if not data or len(data) > MAX_BYTES:
        raise ProviderError("empty_answer")
    return data


def generate(prompt: str, model: str) -> bytes:
    """Rohe Tondaten (mp3). Wirft ProviderError."""
    from hydrahive.llm._config import openrouter_key
    key = openrouter_key()
    if not key:
        raise ProviderError("no_key")
    try:
        return asyncio.run(_request(key, model, prompt))
    except httpx.HTTPError as e:
        raise ProviderError("provider_unreachable") from e
