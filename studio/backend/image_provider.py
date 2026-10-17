"""Bild-Anbieter für das Studio: OpenRouter-Bild-Schnittstelle (`/api/v1/images`), Spec „Bauplan Etappe 3“.

Übernommen vom Vorbild atelier/backend/generate.py (gleicher Aufruf mit Referenzbildern und optionalem Seed), aber als
eigene Kopie, weil das Atelier in Etappe 8 entfällt. Schlüssel und Standardmodell kommen aus dem Kern. Fehler tragen
nur einen Code; den Text für Menschen liefert das Frontend.
"""
from __future__ import annotations

import base64
import binascii
import logging
import math
import re

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


_ACCEPTED = re.compile(r"aspect_ratio[^\"]*\"?[^.]*?Accepted:\s*([0-9a-z:, ]+)", re.IGNORECASE)


def _ratio(v: str) -> float | None:
    a, _, b = v.partition(":")
    try:
        return float(a) / float(b) if b else None
    except (ValueError, ZeroDivisionError):
        return None


def nearest_aspect(wanted: str, accepted: str) -> str | None:
    """Erlaubtes Format, das dem gewünschten am nächsten kommt; None = gewünschtes ist schon erlaubt bzw. nichts passt.
    Nur „auto“ erlaubt → „auto“ (das Modell wählt selbst)."""
    opts = [o.strip() for o in accepted.split(",") if o.strip()]
    if wanted in opts:
        return None
    w = _ratio(wanted)
    ratios = [(o, _ratio(o)) for o in opts]
    fit = [(o, r) for o, r in ratios if r]
    if w and fit:
        return min(fit, key=lambda x: abs(math.log(x[1] / w)))[0]
    return "auto" if "auto" in opts else None


def request_image(*, model: str, prompt: str, references: list[str], aspect_ratio: str, seed: int | None = None) -> bytes:
    from hydrahive.llm._config import openrouter_key
    key = openrouter_key()
    if not key:
        raise ProviderError("no_key")
    try:
        return _request(key, model, prompt, references, aspect_ratio, seed)
    except _FormatRejected as e:                    # Modell kann das Format nicht → einmal mit dem nächsten erlaubten
        logger.info("Studio-Bild: %s kann %s nicht, nehme %s", model, aspect_ratio, e.instead)
        try:
            return _request(key, model, prompt, references, e.instead, seed)
        except _FormatRejected:
            raise ProviderError("provider_rejected") from None


class _FormatRejected(Exception):
    def __init__(self, instead: str) -> None:
        super().__init__(instead)
        self.instead = instead


def _request(key: str, model: str, prompt: str, references: list[str], aspect_ratio: str, seed: int | None) -> bytes:
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
        m = _ACCEPTED.search(resp.text or "") if resp.status_code == 400 else None
        instead = nearest_aspect(aspect_ratio, m.group(1)) if m else None
        if instead:
            raise _FormatRejected(instead)
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
