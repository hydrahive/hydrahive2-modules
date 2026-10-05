"""Clore-Probelauf: öffentlichen Marktplatz lesen, Ertrag gegen Miete rechnen. Nichts mieten.

Nur lesend und ohne Schlüssel (``GET /v1/marketplace``). Spec: mining/docs/clore-dryrun.md.
Ertrag mit derselben Formel wie die Ertragstabelle (``profit.usd_per_day``).
"""
from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from pathlib import Path

import httpx

from . import clore_store, reference, store
from .profit import CoinQuote, usd_per_day

logger = logging.getLogger(__name__)

MARKETPLACE = "https://api.clore.ai/v1/marketplace"
INTERVAL_SECONDS = 900
MIN_ROI = 0.12
MIN_RELIABILITY = 0.90                              # Clore „reliability“: darunter oft offline/abgebrochen
FEE = {"on_demand": 0.05, "spot": 0.0125}          # Mieteranteil der Grundgebühr (10 % / 2,5 % hälftig)
SAFETY = {"reference": 0.85, "measured": 0.92}      # konservativer Abschlag auf den Ertrag
MIN_PROP_DISCOUNT = 0.10
_OWN_FILE = Path(__file__).with_name("clore_benchmarks.json")
_GPU_RE = re.compile(r"^\s*(\d{1,2})\s*x\s+(.+?)\s*$", re.IGNORECASE)
# Rechenzentrumskarten schreibt Clore ohne Hersteller, Bauform und Speicher am Stück: „Tesla V100SXM232GB“
_DC_RE = re.compile(r"^(?:nvidia\s+)?tesla\s+([a-z]\d{1,3})(?:sxm\d?|pcie)?(?:\d+\s*gb)?$", re.IGNORECASE)


class CloreError(RuntimeError):
    pass


def parse_gpu(text: str) -> tuple[int, str] | None:
    """„8x Tesla V100SXM232GB“ → (8, "nvidia-v100"). Gemischt/unlesbar → None."""
    m = _GPU_RE.match(text or "")
    if not m or int(m.group(1)) < 1:
        return None
    name = m.group(2).strip()
    if name.lower().startswith("mixed"):
        return None
    dc = _DC_RE.match(name)
    if dc:
        return int(m.group(1)), f"nvidia-{dc.group(1).lower()}"
    s = re.sub(r"\b(geforce|radeon)\b", "", name.lower())
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return (int(m.group(1)), s) if s else None


@lru_cache(maxsize=1)
def _own() -> dict[str, dict[str, float]]:
    """Eigene Messwerte {gpu: {coin: H/s je Karte}} – Vorrang vor Herstellerwerten."""
    try:
        return {k: v["hashrates"] for k, v in json.loads(_OWN_FILE.read_text())["gpus"].items()}
    except (OSError, ValueError, KeyError, TypeError):
        return {}


def hashrates_for(gpu: str) -> tuple[dict[str, float], str]:
    """({coin: H/s je Karte}, Herkunft). Herkunft „measured“ | „reference“ | „none“."""
    own = _own().get(gpu)
    if own:
        return dict(own), "measured"
    for key in (gpu, f"{gpu}-16gb", f"{gpu}-8gb"):              # Clore nennt die Speichergröße oft nicht
        ref = reference.hashrates(key)
        if ref:
            return ref, "reference"
    return {}, "none"


def _usd(v) -> float | None:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0 else None


def costs(server: dict) -> tuple[float | None, float | None]:
    """(On-Demand, Spot) in USD/Tag inkl. Mietergebühr. Spot = kleinstes Mindestgebot."""
    price = server.get("price") if isinstance(server.get("price"), dict) else {}
    usd = price.get("usd") if isinstance(price.get("usd"), dict) else {}
    od = _usd(usd.get("on_demand_usd")) or _usd(usd.get("on_demand_clore")) or _usd(usd.get("on_demand_btc"))
    orig = price.get("original_usd") if isinstance(price.get("original_usd"), dict) else {}
    spots = [_usd(v.get("spot")) for v in orig.values() if isinstance(v, dict)]
    spot = min((s for s in spots if s), default=None)
    return (od * (1 + FEE["on_demand"]) if od else None, spot * (1 + FEE["spot"]) if spot else None)


def _roi(revenue: float, cost: float | None) -> float | None:
    return (revenue - cost) / cost if cost else None


def evaluate(server: dict, quotes: dict[str, CoinQuote], *, prop_discount: float) -> dict:
    """Ein Server → Bewertung. ``status``: rated | rented | gpu_unknown | no_benchmark | no_price."""
    out = {"server_id": server.get("id"), "reliability": server.get("reliability"), "mrl": server.get("mrl")}
    if server.get("rented"):
        return {**out, "status": "rented"}
    parsed = parse_gpu(str((server.get("specs") or {}).get("gpu") or ""))
    if not parsed:
        return {**out, "status": "gpu_unknown"}
    count, gpu = parsed
    hs, source = hashrates_for(gpu)
    discount = max(prop_discount, MIN_PROP_DISCOUNT)
    cands = [(usd_per_day(q, h * count, prop_discount=discount) or 0.0, c)
             for c, h in hs.items() if (q := quotes.get(c)) is not None]
    cands = [x for x in cands if x[0] > 0]
    if not cands:
        return {**out, "status": "no_benchmark", "gpu": gpu, "count": count}
    revenue, coin = max(cands)
    revenue *= SAFETY[source]
    cost_od, cost_spot = costs(server)
    if cost_od is None and cost_spot is None:
        return {**out, "status": "no_price", "gpu": gpu, "count": count}
    roi_od, roi_spot = _roi(revenue, cost_od), _roi(revenue, cost_spot)
    rel = server.get("reliability")
    reliable = isinstance(rel, (int, float)) and not isinstance(rel, bool) and rel >= MIN_RELIABILITY
    return {**out, "status": "rated", "gpu": gpu, "count": count, "coin": coin, "source": source,
            "revenue": revenue, "cost_od": cost_od, "cost_spot": cost_spot, "roi_od": roi_od, "roi_spot": roi_spot,
            "hit_od": reliable and roi_od is not None and roi_od >= MIN_ROI,
            "hit_spot": reliable and roi_spot is not None and roi_spot >= MIN_ROI}


def scan(servers: list[dict], quotes: dict[str, CoinQuote], *, prop_discount: float) -> dict:
    rated = [evaluate(s, quotes, prop_discount=prop_discount) for s in servers if isinstance(s, dict)]
    free = [r for r in rated if r["status"] != "rented"]
    ok = [r for r in free if r["status"] == "rated"]
    hits = [r for r in ok if r["hit_od"] or r["hit_spot"]]
    rois = [x for r in ok for x in (r["roi_od"], r["roi_spot"]) if x is not None]
    run = {"ok": True, "free": len(free), "rated": len(ok), "hits": len(hits), "best_roi": max(rois, default=None)}
    clore_store.save_run(run, hits)
    return run


async def fetch_marketplace() -> list[dict]:
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0),
                                     headers={"User-Agent": "HydraHive-Mining"}) as http:
            r = await http.get(MARKETPLACE)
            r.raise_for_status()
            data = r.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise CloreError(str(exc)[:200]) from exc
    if not isinstance(data, dict) or data.get("code") != 0 or not isinstance(data.get("servers"), list):
        raise CloreError(f"unexpected_response:{str(data)[:80] if not isinstance(data, dict) else data.get('code')}")
    return data["servers"]


async def job() -> None:
    cfg = store.get_config()
    if not cfg.get("clore_dryrun"):
        return
    quotes = {q.coin: q for q in store.load_quotes()[0]}
    try:
        servers = await fetch_marketplace()
    except CloreError as exc:
        logger.warning("Mining: Clore-Marktplatz nicht lesbar: %s", exc)
        clore_store.save_run({"ok": False, "free": 0, "rated": 0, "hits": 0, "best_roi": None, "error": str(exc)}, [])
        return
    if not quotes:
        clore_store.save_run({"ok": False, "free": 0, "rated": 0, "hits": 0, "best_roi": None,
                              "error": "no_kryptex_quotes"}, [])
        return
    scan(servers, quotes, prop_discount=float(cfg.get("prop_discount") or 0.0))
