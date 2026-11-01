"""Clients: aktive (stat/sta) und bekannte (rest/user) zusammenführen – nur ausgewählte Felder.

Richtung: UniFi zählt aus Sicht des Netzes. tx = zum Client gesendet = beim Client „herunter“ (down),
rx = vom Client empfangen = „hoch“ (up). Bei Kabel-Clients stehen die Werte in wired-tx_bytes/wired-rx_bytes.
"""
from __future__ import annotations

BANDS = {"ng": "2.4", "na": "5", "6e": "6"}


def _name(x: dict, known: dict) -> str:
    for v in (known.get("name"), x.get("name"), x.get("hostname"), known.get("hostname")):
        if v:
            return v
    mac = x.get("mac") or ""
    vendor = x.get("oui") or known.get("oui")
    return f"{vendor} ({mac[-5:]})" if vendor else mac


def _row(x: dict, known: dict, online: bool, devs: dict[str, str]) -> dict:
    wired = bool(x.get("is_wired", known.get("is_wired")))
    up_mac = (x.get("sw_mac") if wired else x.get("ap_mac")) or known.get("last_uplink_mac")
    down = x.get("wired-tx_bytes") if wired else x.get("tx_bytes")
    up = x.get("wired-rx_bytes") if wired else x.get("rx_bytes")
    return {"mac": x.get("mac"), "name": _name(x, known), "vendor": x.get("oui") or known.get("oui"),
            "ip": x.get("ip") or x.get("last_ip") or known.get("last_ip"), "online": online, "wired": wired,
            "guest": bool(x.get("is_guest") or known.get("is_guest")), "network": x.get("network"),
            "essid": None if wired else x.get("essid"), "band": None if wired else BANDS.get(x.get("radio")),
            "signal": None if wired else x.get("signal"), "satisfaction": x.get("satisfaction"),
            "uplink_name": devs.get(up_mac) or x.get("last_uplink_name") or known.get("last_uplink_name"),
            "uplink_port": x.get("sw_port"), "uptime_s": x.get("uptime") if online else None,
            "down_bytes": down, "up_bytes": up,
            "first_seen": x.get("first_seen") or known.get("first_seen"),
            "last_seen": x.get("last_seen") or known.get("last_seen"),
            "fixed_ip": bool(x.get("use_fixedip") or known.get("use_fixedip"))}


def clients(sta: dict, user: dict, devices: list[dict]) -> list[dict]:
    devs = {d["mac"]: d["name"] for d in devices}
    known = {u["mac"]: u for u in user.get("data", []) if isinstance(u, dict) and u.get("mac")}
    rows = {}
    for x in sta.get("data", []):
        if isinstance(x, dict) and x.get("mac"):
            rows[x["mac"]] = _row(x, known.get(x["mac"], {}), True, devs)
    for mac, u in known.items():
        if mac not in rows:
            rows[mac] = _row(u, u, False, devs)
    return sorted(rows.values(), key=lambda r: (not r["online"], r["name"].lower()))
