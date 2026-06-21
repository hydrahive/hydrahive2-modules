"""OG-Bilder als data:-URIs einbetten.

Die App-CSP blockt externe Bild-Domains, erlaubt aber `img-src data:`. Indem wir die
Bilder serverseitig (SSRF-sicher) holen und base64 einbetten, rendern sie im iframe
ohne CSP-Lockerung. Der Report wird damit voll self-contained.
"""
from __future__ import annotations

import asyncio
import base64
import logging

from hydrahive.net.ssrf import SsrfBlocked, safe_async_client

logger = logging.getLogger(__name__)

_MAX_BYTES = 700_000   # zu große Bilder überspringen (Report nicht aufblähen)
_TIMEOUT = 5
_CONCURRENCY = 4


async def _to_data_uri(url: str) -> str:
    try:
        async with safe_async_client(url, timeout=_TIMEOUT) as client:
            r = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (HydraHive DeepResearch)"})
    except SsrfBlocked:
        return ""
    except Exception as e:  # noqa: BLE001 - best-effort, totes Bild darf Report nicht killen
        logger.info("deepresearch: og-image fetch fehlgeschlagen %s: %s", url, e)
        return ""
    ctype = r.headers.get("content-type", "").split(";")[0].strip().lower()
    data = r.content
    if not ctype.startswith("image/") or not data or len(data) > _MAX_BYTES:
        return ""
    return f"data:{ctype};base64,{base64.b64encode(data).decode('ascii')}"


async def embed_images(sources: list[dict]) -> list[dict]:
    """Kopie der Quellen mit image=data:-URI (oder '' wenn nicht ladbar)."""
    sem = asyncio.Semaphore(_CONCURRENCY)

    async def one(s: dict) -> dict:
        img = (s.get("image") or "").strip()
        if not img.startswith(("http://", "https://")):
            return {**s, "image": ""}
        async with sem:
            return {**s, "image": await _to_data_uri(img)}

    return list(await asyncio.gather(*(one(s) for s in sources)))
