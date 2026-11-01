"""Daten der Dream Machine für Geräte/Clients/Netz holen – mit Zwischenspeicher (30 s) und letztem Stand.

Ist die Dream Machine nicht erreichbar, liefert get() den letzten Stand mit stale=True und dem Fehlercode.
Gab es noch nie einen Stand, wird der Fehler weitergereicht.
"""
from __future__ import annotations

import time

from . import collect, config_store
from .errors import NetError

TTL = 30.0
S = "/proxy/network/api/s/default"
PATHS = {"device": f"{S}/stat/device", "sta": f"{S}/stat/sta", "user": f"{S}/rest/user",
         "networkconf": f"{S}/rest/networkconf", "wlanconf": f"{S}/rest/wlanconf",
         "portforward": f"{S}/rest/portforward", "firewall": f"{S}/rest/firewallrule",
         "routing": f"{S}/rest/routing", "topology": "/proxy/network/v2/api/site/default/topology"}
_cache: dict[str, tuple[float, object]] = {}
_last: dict[str, tuple[float, object]] = {}


def _clock() -> float:
    return time.time()


def clear_cache() -> None:
    _cache.clear()
    _last.clear()


def _cfg() -> dict:
    cfg = config_store.get()
    if not collect._ready(cfg):
        raise NetError("network_not_configured")
    return cfg


async def get(keys: tuple[str, ...]) -> dict:
    """{key: daten, …, "_stale": bool, "_error": code|None, "_at": Zeit des ältesten Teils}."""
    now = _clock()
    out: dict = {"_stale": False, "_error": None, "_at": now}
    missing = [k for k in keys if k not in _cache or now - _cache[k][0] > TTL]
    if missing:
        udm = collect._udm(_cfg())
        for k in missing:
            try:
                _cache[k] = (now, await udm.get(PATHS[k]))
                _last[k] = _cache[k]
            except NetError as e:
                if k not in _last:
                    raise
                _cache.pop(k, None)
                out["_stale"], out["_error"] = True, e.code
    for k in keys:
        at, data = _cache.get(k) or _last[k]
        out[k] = data
        out["_at"] = min(out["_at"], at)
    return out


def peek(key: str):
    """Letzter bekannter Stand ohne Abruf (für Zahlen in der Übersicht)."""
    hit = _cache.get(key) or _last.get(key)
    return hit[1] if hit else None
