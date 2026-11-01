"""Geräte der Dream Machine (stat/device) in schlanke Zeilen übersetzen – nur ausgewählte Felder (Positivliste)."""
from __future__ import annotations

KINDS = {"udm": "gateway", "ugw": "gateway", "uxg": "gateway", "usw": "switch", "uap": "ap"}
ORDER = {"gateway": 0, "switch": 1, "ap": 2, "other": 3}
STATES = {0: "offline", 1: "online", 2: "pending", 4: "upgrading", 5: "provisioning", 6: "heartbeat_missed"}
BANDS = {"ng": "2.4", "na": "5", "6e": "6"}


def _num(v) -> float | None:
    try:
        return float(v) if v is not None and v != "" else None
    except (TypeError, ValueError):
        return None


def _port(p: dict) -> dict:
    up = bool(p.get("up"))
    return {"idx": p.get("port_idx"), "name": p.get("name"), "up": up, "speed": p.get("speed") if up else None,
            "uplink": bool(p.get("is_uplink")), "poe": p.get("poe_enable"), "poe_w": _num(p.get("poe_power")),
            "media": p.get("media"), "tx_bytes": p.get("tx_bytes"), "rx_bytes": p.get("rx_bytes"),
            "errors": (p.get("rx_errors") or 0) + (p.get("tx_errors") or 0)}


def _radio(r: dict) -> dict:
    return {"band": BANDS.get(r.get("radio"), r.get("radio")), "channel": r.get("channel"),
            "tx_power": r.get("tx_power"), "utilization": r.get("cu_total"), "clients": r.get("num_sta"),
            "satisfaction": r.get("satisfaction")}


def device(x: dict) -> dict:
    kind = KINDS.get(x.get("type"), "other")
    stats = x.get("system-stats") or {}
    up = x.get("uplink") or {}
    return {"mac": x.get("mac"), "name": x.get("name") or x.get("mac"), "model": x.get("model"), "kind": kind,
            "state": STATES.get(x.get("state"), "unknown"), "adopted": bool(x.get("adopted")), "ip": x.get("ip"),
            "version": x.get("version"), "upgradable": bool(x.get("upgradable")),
            "upgrade_to": x.get("upgrade_to_firmware"), "uptime_s": x.get("uptime"), "clients": x.get("num_sta"),
            "cpu": _num(stats.get("cpu")), "mem": _num(stats.get("mem")), "satisfaction": x.get("satisfaction"),
            "temps": [{"name": t.get("name"), "value": t.get("value")} for t in x.get("temperatures") or []],
            "tx_bytes": x.get("tx_bytes"), "rx_bytes": x.get("rx_bytes"),
            "uplink": ({"mac": up.get("uplink_mac"), "name": None, "port": up.get("uplink_remote_port"),
                        "speed": up.get("speed")} if up.get("uplink_mac") else None),
            "ports": sorted((_port(p) for p in x.get("port_table") or []), key=lambda p: p["idx"] or 0),
            "radios": [_radio(r) for r in x.get("radio_table_stats") or []]}


def devices(raw: dict) -> list[dict]:
    items = [device(x) for x in raw.get("data", []) if isinstance(x, dict)]
    names = {d["mac"]: d["name"] for d in items}
    for d in items:
        if d["uplink"]:
            d["uplink"]["name"] = names.get(d["uplink"]["mac"])
    return sorted(items, key=lambda d: (not d["adopted"], ORDER[d["kind"]], d["name"].lower()))
