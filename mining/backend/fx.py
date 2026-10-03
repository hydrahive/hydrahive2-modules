"""USD→EUR über den EZB-Referenzkurs (täglich, öffentlich, ohne Schlüssel)."""
from __future__ import annotations

import logging
import re

import httpx

logger = logging.getLogger(__name__)

ECB_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
_USD_RE = re.compile(r"currency=['\"]USD['\"]\s+rate=['\"]([0-9.]+)['\"]")


def parse_usd_rate(xml: str) -> float | None:
    """1 EUR = x USD aus dem EZB-XML. None, wenn nicht gefunden/unplausibel."""
    m = _USD_RE.search(xml or "")
    if not m:
        return None
    rate = float(m.group(1))
    return rate if 0.3 < rate < 3.0 else None


async def fetch_usd_per_eur() -> float | None:
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=8.0)) as http:
            r = await http.get(ECB_URL)
            r.raise_for_status()
            return parse_usd_rate(r.text)
    except httpx.HTTPError as exc:
        logger.warning("Mining: EZB-Kurs nicht abrufbar: %s", exc)
        return None
