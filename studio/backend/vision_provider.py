"""Ein Bild beschreiben lassen (Spec „C2 im Detail“): OpenRouter chat/completions mit einem image_url-Block.

Vorbild: Kern-Werkzeug hydrahive/tools/analyze_image.py (eigene schlanke Fassung, Module nutzen nur Kern-Bausteine wie
den Schlüssel). Standardmodell günstig und schnell; das Drehbuch kann unter „Modelle“ ein anderes eintragen.
"""
from __future__ import annotations

import logging

import httpx

logger = logging.getLogger("hhmod_studio.vision")

URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "google/gemini-2.5-flash"
TIMEOUT = 60.0


class VisionError(RuntimeError):
    """Fehlercode: no_key, provider_rejected, provider_unreachable, empty_answer."""


def _text(data: dict) -> str:
    choices = data.get("choices") or []
    content = (choices[0].get("message") or {}).get("content") if choices and isinstance(choices[0], dict) else None
    if isinstance(content, list):
        content = "".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return content.strip() if isinstance(content, str) else ""


async def ask(*, model: str, image_url: str, prompt: str) -> str:
    from hydrahive.llm._config import openrouter_key
    key = openrouter_key()
    if not key:
        raise VisionError("no_key")
    payload = {"model": model, "messages": [{"role": "user", "content": [
        {"type": "image_url", "image_url": {"url": image_url}}, {"type": "text", "text": prompt}]}]}
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(URL, headers={"Authorization": f"Bearer {key}"}, json=payload)
    except httpx.HTTPError as e:
        raise VisionError("provider_unreachable") from e
    if resp.status_code >= 400:
        logger.warning("Studio-Bildbeschreibung HTTP %s: %s", resp.status_code, resp.text[:300])
        raise VisionError("provider_rejected")
    try:
        text = _text(resp.json())
    except ValueError as e:
        raise VisionError("empty_answer") from e
    if not text:
        raise VisionError("empty_answer")
    return text
