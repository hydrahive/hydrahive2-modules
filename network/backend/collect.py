"""Sammler (über ctx.register_job): eigene Messung jede Minute, Dream Machine alle 5 Minuten und stündlich.

Die Dream Machine hält 5-Minuten-Werte 24 h, Stundenwerte 7 Tage, Tageswerte 90 Tage – hier bleiben sie.
Fehler eines Geräts werden gemerkt (config.last_error), der Sammler läuft weiter.
"""
from __future__ import annotations

import asyncio
import logging
import time

from . import (
    classify,
    config_store,
    creds,
    fritz_igd,
    netcheck,
    probe,
    store,
    unifi_parse,
)
from .errors import NetError
from .unifi_client import Udm

logger = logging.getLogger(__name__)
INTERNET_TARGETS = ("1.1.1.1", "9.9.9.9")
_H, _D = 3600, 86400
_LOG = "/proxy/network/v2/api/site/default/system-log/all"
_REPORT = "/proxy/network/api/s/default/stat/report/"
_ATTRS = ["time", "wan-tx_bytes", "wan-rx_bytes", "latency_avg", "latency_min", "latency_max"]
_PAGE = 500


def _host(url: str | None) -> str | None:
    try:
        return netcheck.udm_url(url)[0] if url else None
    except NetError:
        return None


async def _ip_ping(host: str | None) -> dict:
    return await probe.ping(host) if host and probe.valid_target(host) else {"loss": None, "avg": None}


async def tick_minute(now: int | None = None) -> dict:
    ts = int(now if now is not None else time.time()) // 60 * 60
    cfg = config_store.get() or {}
    fritz_host = cfg.get("fritz_host")
    inet, lan, fr, fst = await asyncio.gather(
        asyncio.gather(*(probe.ping(t) for t in INTERNET_TARGETS)), _ip_ping(_host(cfg.get("udm_url"))),
        _ip_ping(fritz_host), fritz_igd.status(fritz_host) if fritz_host else asyncio.sleep(0, {}))
    i = probe.combine(list(inet))
    s = {"ts": ts, "lan_loss": lan.get("loss"), "lan_rtt": lan.get("avg"), "fritz_loss": fr.get("loss"),
         "fritz_rtt": fr.get("avg"), "inet_loss": i["loss"], "inet_rtt_min": i["min"], "inet_rtt_avg": i["avg"],
         "inet_rtt_max": i["max"], "inet_jitter": i["mdev"], "fritz_link": fst.get("link"),
         "fritz_conn": fst.get("conn"), "fritz_access": fst.get("access"),
         "path": classify.path(i["loss"], fst.get("link") if fritz_host else None, fst.get("ext_ip"))}
    store.add_sample(s)
    return s


def _udm(cfg: dict) -> Udm:
    return Udm(cfg["udm_url"], creds.udm_key(cfg["owner"], cfg["udm_credential"]), cfg.get("udm_pin"))


def _ready(cfg: dict | None) -> bool:
    return bool(cfg and cfg.get("udm_url") and cfg.get("udm_credential"))


async def _report(c: Udm, name: str, start: int, end: int, attrs: list[str] | None = None) -> dict:
    return await c.post(_REPORT + name, {"attrs": attrs or _ATTRS, "start": start * 1000, "end": end * 1000})


async def tick_udm(now: int | None = None) -> None:
    t = int(now if now is not None else time.time())
    cfg = config_store.get()
    if not _ready(cfg):
        return
    try:
        c = _udm(cfg)
        status = unifi_parse.health(await c.get("/proxy/network/api/s/default/stat/health"))
        store.put_series(unifi_parse.series("5min", await _report(c, "5minutes.site", t - _D, t)))
        st = await _report(c, "archive.speedtest", t - 2 * _D, t,
                           ["xput_download", "xput_upload", "latency", "rundate", "server"])
        store.add_speedtests(unifi_parse.speedtests(st))
    except NetError as e:
        config_store.set_status(status=None, at=t, error=e.code)
        return
    config_store.set_status(status=status, at=t, error=None)


async def _events(c: Udm, start: int, end: int) -> int:
    n = 0
    for page in range(40):
        d = await c.post(_LOG, {"timestampFrom": start * 1000, "timestampTo": end * 1000, "pageSize": _PAGE,
                                "pageNumber": page})
        rows = d.get("data", []) if isinstance(d, dict) else []
        n += store.add_events(unifi_parse.events({"data": rows}))
        if len(rows) < _PAGE:
            break
    return n


async def tick_hourly(now: int | None = None) -> dict:
    t = int(now if now is not None else time.time())
    cfg = config_store.get()
    out = {"events": 0, "speedtests": 0}
    if not _ready(cfg):
        return out
    last = store.last_event_ts("udm")
    try:
        c = _udm(cfg)
        out["events"] = await _events(c, last - 2 * _H if last else t - 90 * _D, t)
        st = await _report(c, "archive.speedtest", t - 90 * _D, t,
                           ["xput_download", "xput_upload", "latency", "rundate", "server"])
        out["speedtests"] = store.add_speedtests(unifi_parse.speedtests(st))
        store.put_series(unifi_parse.series("hour", await _report(c, "hourly.site", t - 7 * _D, t)))
        store.put_series(unifi_parse.series("day", await _report(c, "daily.site", t - 90 * _D, t)))
    except NetError as e:
        config_store.set_status(status=None, at=t, error=e.code)
        return out
    config_store.set_full_sync(t)
    return out


async def job_minute() -> None:
    await tick_minute()


async def job_udm() -> None:
    await tick_udm()


async def job_hourly() -> None:
    await tick_hourly()
