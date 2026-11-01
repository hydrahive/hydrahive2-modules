"""Ansehen (module.network, prüft das Modul-Tor des Kerns): Überblick, Messung, Störungen, Speedtests."""
from __future__ import annotations

import time
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from hydrahive.api.middleware.auth import AuthPrincipal, require_principal

from . import config_store, outages, store

router = APIRouter()
Viewer = Annotated[AuthPrincipal, Depends(require_principal)]
# Kalendertage wie im Kern-Dashboard: deutsche Zeit (Kern api/routes/_dashboard_helpers.py).
DAY_TZ = ZoneInfo("Europe/Berlin")
Days = Annotated[int, Query(ge=1, le=366)]
Now = Annotated[int | None, Query(ge=0)]


def _now(now: int | None) -> int:
    return now if now is not None else int(time.time())


@router.get("/overview")
def overview(p: Viewer):
    cfg = config_store.get()
    st = store.speedtests(0, 2**62)
    return {"configured": bool(cfg and cfg.get("udm_url")), "latest": store.latest_sample(),
            "udm": (cfg or {}).get("last_status"), "udm_at": (cfg or {}).get("last_status_at"),
            "udm_error": (cfg or {}).get("last_error"), "udm_confirmed": bool((cfg or {}).get("udm_pin")),
            "fritz": bool((cfg or {}).get("fritz_host")),
            "plan": {"down": (cfg or {}).get("plan_down_mbit"), "up": (cfg or {}).get("plan_up_mbit")},
            "last_speedtest": st[-1] if st else None}


@router.get("/samples")
def samples(p: Viewer, hours: Annotated[int, Query(ge=1, le=24 * 31)] = 24, now: Now = None):
    end = _now(now)
    return {"items": store.samples(end - hours * 3600, end)}


@router.get("/outages")
def get_outages(p: Viewer, days: Days = 7, now: Now = None):
    end = _now(now)
    start = end - days * 86400
    items = outages.merge(outages.from_udm(store.events(start, end + 86400))
                          + outages.from_samples(store.samples(start, end)))
    items = [o for o in items if o["end"] >= start]
    return {"items": sorted(items, key=lambda o: o["start"], reverse=True),
            "per_day": outages.per_day(items, "wan", DAY_TZ),
            "per_day_cable": outages.per_day(items, "cable", DAY_TZ),
            "per_day_internet": outages.per_day(items, "internet", DAY_TZ)}


@router.get("/speedtests")
def get_speedtests(p: Viewer, days: Days = 30, now: Now = None):
    end = _now(now)
    return {"items": store.speedtests(end - days * 86400, end)}


@router.get("/series")
def get_series(p: Viewer, scale: Annotated[str, Query(pattern="^(5min|hour|day)$")] = "hour", days: Days = 7,
               now: Now = None):
    end = _now(now)
    return {"items": store.series(scale, end - days * 86400, end)}
