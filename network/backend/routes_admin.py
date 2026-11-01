"""Ansehen 0.2.0 (module.network): Geräte, Clients, Netz, Verkehr aus der Dream Machine. Nur lesend."""
from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status
from hydrahive.api.middleware.auth import AuthPrincipal, require_principal
from hydrahive.api.middleware.errors import coded

from . import admin_data, clients_parse, devices_parse, net_parse
from .errors import NetError

router = APIRouter()
Viewer = Annotated[AuthPrincipal, Depends(require_principal)]
_HTTP = {"network_not_configured": 409, "network_cert_unconfirmed": 409, "network_cert_changed": 409,
         "network_credential_invalid": 409}
TOP_CLIENTS = 20


async def _load(*keys: str) -> dict:
    try:
        return await admin_data.get(keys)
    except NetError as e:
        raise coded(_HTTP.get(e.code, status.HTTP_502_BAD_GATEWAY), e.code) from None


def _meta(d: dict) -> dict:
    return {"stale": d["_stale"], "error": d["_error"], "fetched_at": int(d["_at"])}


def _clients(d: dict) -> list[dict]:
    return clients_parse.clients(d["sta"], d["user"], devices_parse.devices(d["device"]))


@router.get("/devices")
async def get_devices(p: Viewer):
    d = await _load("device")
    return {"items": devices_parse.devices(d["device"]), **_meta(d)}


@router.get("/clients")
async def get_clients(p: Viewer, status_: Annotated[Literal["all", "online", "offline"], Query(alias="status")] = "all",
                      link: Literal["all", "wired", "wireless"] = "all",
                      q: Annotated[str, Query(max_length=100)] = ""):
    d = await _load("device", "sta", "user")
    rows = _clients(d)
    online = [r for r in rows if r["online"]]
    counts = {"total": len(rows), "online": len(online), "wireless": sum(1 for r in online if not r["wired"])}
    if status_ != "all":
        rows = [r for r in rows if r["online"] == (status_ == "online")]
    if link != "all":
        rows = [r for r in rows if r["wired"] == (link == "wired")]
    needle = q.strip().lower()
    if needle:
        rows = [r for r in rows if any(needle in (r.get(k) or "").lower() for k in ("name", "vendor", "ip", "mac"))]
    return {"items": rows, **counts, **_meta(d)}


@router.get("/net")
async def get_net(p: Viewer):
    d = await _load("networkconf", "wlanconf", "portforward", "firewall", "routing", "topology")
    return {"tree": net_parse.tree(d["topology"]),
            **net_parse.net(d["networkconf"], d["wlanconf"], d["portforward"], d["firewall"], d["routing"]), **_meta(d)}


@router.get("/traffic")
async def get_traffic(p: Viewer):
    d = await _load("device", "sta", "user")
    online = [r for r in _clients(d) if r["online"]]
    top = sorted(online, key=lambda r: -((r["down_bytes"] or 0) + (r["up_bytes"] or 0)))[:TOP_CLIENTS]
    devs = [{"name": x["name"], "kind": x["kind"], "tx_bytes": x["tx_bytes"], "rx_bytes": x["rx_bytes"],
             "ports": [{"idx": pt["idx"], "name": pt["name"], "up": pt["up"], "tx_bytes": pt["tx_bytes"],
                        "rx_bytes": pt["rx_bytes"]} for pt in x["ports"]]}
            for x in devices_parse.devices(d["device"]) if x["adopted"]]
    return {"clients": [{**r, "down_bytes": r["down_bytes"] or 0, "up_bytes": r["up_bytes"] or 0} for r in top],
            "devices": devs, **_meta(d)}


def counts() -> dict | None:
    """Zahlen für die Übersicht aus dem letzten Stand (kein Abruf)."""
    dev, sta = admin_data.peek("device"), admin_data.peek("sta")
    if dev is None or sta is None:
        return None
    items = devices_parse.devices(dev)
    rows = [x for x in sta.get("data", []) if isinstance(x, dict)]
    wl = sum(1 for x in rows if not x.get("is_wired"))
    return {"devices": len(items), "devices_online": sum(1 for x in items if x["state"] == "online"),
            "clients": len(rows), "wireless": wl, "wired": len(rows) - wl}
