"""Bild-Anbieter für das Studio: OpenRouter-Bild-Schnittstelle (`/api/v1/images`), Spec „Bauplan Etappe 3“.

Übernommen vom Vorbild atelier/backend/generate.py (gleicher Aufruf mit Referenzbildern und optionalem Seed), aber als
eigene Kopie, weil das Atelier in Etappe 8 entfällt. Schlüssel und Standardmodell kommen aus dem Kern. Fehler tragen
nur einen Code; den Text für Menschen liefert das Frontend.
"""
from __future__ import annotations

import base64
import binascii
import logging

import httpx

logger = logging.getLogger("hhmod_studio.image")

URL = "https://openrouter.ai/api/v1/images"
TIMEOUT = 180.0
MAX_BYTES = 30 * 1024 * 1024


class ProviderError(RuntimeError):
    """Fehlercode: no_key, provider_rejected, provider_unreachable, empty_answer, bad_image."""


def server_default_model() -> str:
    from hydrahive.llm.media_models import get_media_model
    return get_media_model("image")


def request_image(*, model: str, prompt: str, references: list[str], aspect_ratio: str, seed: int | None = None) -> bytes:
    from hydrahive.llm._config import openrouter_key
    key = openrouter_key()
    if not key:
        raise ProviderError("no_key")
    payload: dict = {"model": model, "prompt": prompt, "aspect_ratio": aspect_ratio}
    if references:
        payload["input_references"] = [{"type": "image_url", "image_url": {"url": u}} for u in references]
    if seed is not None:
        payload["seed"] = seed
    try:
        resp = httpx.post(URL, json=payload, headers={"Authorization": f"Bearer {key}"}, timeout=TIMEOUT)
    except httpx.HTTPError as e:
        logger.warning("Studio-Bild: Anbieter nicht erreichbar: %s", e)
        raise ProviderError("provider_unreachable") from e
    if resp.status_code != 200:
        logger.warning("Studio-Bild: Anbieter antwortet %s: %s", resp.status_code, resp.text[:300])
        raise ProviderError("provider_rejected")
    try:
        data = resp.json().get("data") or []
        b64 = (data[0] or {}).get("b64_json") if data else None
        if not b64:
            raise ProviderError("empty_answer")
        return base64.b64decode(b64, validate=True)
    except (ValueError, binascii.Error, AttributeError, IndexError) as e:
        raise ProviderError("empty_answer") from e


def image_kind(raw: bytes) -> str | None:
    """Bildart an den ersten Bytes erkennen (png/jpg/webp). Alles andere, auch zu Großes, ist kein Bild."""
    if not raw or len(raw) > MAX_BYTES:
        return None
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if raw.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return "webp"
    return None
