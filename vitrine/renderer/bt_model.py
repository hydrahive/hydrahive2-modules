"""S7: reine Bluetooth-Logik ohne Bus – Adresse prüfen, Art, Signal, Zwillinge zusammenfassen, Sortierung.

Ein Gerät (dict) hat: address, address_type, name, rssi, paired, connected, icon, le.
„Zwillinge“: Multi-Mode-Tastaturen melden sich mit zwei Adressen (Rapoo am 21.10.: „RAPOO BT3.0 KB“ klassisch und
„RAPOO BT4.0 KB“ LE). Gleicher Name ohne die BT-Kennung + gleiche Herstellerkennung (erste 3 Bytes) → eine Zeile.
Gekoppelt wird zuerst die klassische Adresse: die LE-Kopplung brach am 21.10. mit `auth failed 0x05` ab.
"""
from __future__ import annotations

import re

_ADDR = re.compile(r"^[0-9A-F]{2}(?::[0-9A-F]{2}){5}$")
_BT_TAG = re.compile(r"\s*\b(?:BT\s?[2-5]\.\d|LE|BLE)\b\s*", re.IGNORECASE)
NAME_MAX = 60
UNKNOWN = "Unbekanntes Gerät"
WEAK_DBM = -85        # stärkstes Gerät schwächer → „Antennen prüfen“ (21.10.: ohne Antenne −98 … −106)
MORE_DBM = -90        # ohne Namen und schwächer → unter „Weitere Geräte“

_KINDS = (("input-keyboard", "keyboard"), ("input-mouse", "mouse"), ("input-tablet", "mouse"),
          ("audio-head", "headphones"), ("audio-", "speaker"), ("phone", "phone"))


def address(raw: object) -> str | None:
    """Gültige Adresse in Großbuchstaben, sonst None. Kein Trimmen: genau das Format oder nichts."""
    if not isinstance(raw, str):
        return None
    up = raw.upper()
    return up if _ADDR.match(up) else None


def kind(icon: str | None) -> str:
    for prefix, art in _KINDS:
        if icon and icon.startswith(prefix):
            return art
    return "other"


def bars(rssi: int | None) -> int:
    if rssi is None:
        return 0
    if rssi >= -60:
        return 4
    if rssi >= -75:
        return 3
    if rssi >= -90:
        return 2
    return 1


def _base_name(name: str | None) -> str:
    return re.sub(r"\s+", " ", _BT_TAG.sub(" ", name or "")).strip()


def _key(d: dict) -> tuple:
    base = _base_name(d.get("name"))
    if not base:
        return ("addr", d["address"])                 # ohne Namen nie zusammenfassen
    return ("twin", d["address"][:8], base.casefold())


def _classic_first(d: dict) -> tuple:
    return (bool(d.get("le")), -(d.get("rssi") if d.get("rssi") is not None else -999))


def _row(group: list[dict]) -> dict:
    group = sorted(group, key=_classic_first)
    rssis = [d["rssi"] for d in group if d.get("rssi") is not None]
    rssi = max(rssis) if rssis else None
    raw_name = group[0].get("name") if len(group) == 1 else _base_name(group[0].get("name"))
    name = (raw_name or "").strip()[:NAME_MAX] or UNKNOWN
    paired = any(d.get("paired") for d in group)
    return {
        "name": name,
        "addresses": [d["address"] for d in group],
        "kind": kind(next((d.get("icon") for d in group if d.get("icon")), None)),
        "rssi": rssi,
        "bars": bars(rssi),
        "paired": paired,
        "connected": any(d.get("connected") for d in group),
        "more": not paired and name == UNKNOWN and (rssi is None or rssi < MORE_DBM),
    }


def rows(devices: list[dict]) -> list[dict]:
    """Eine Zeile je Gerät (Zwillinge zusammen). Gekoppelte zuerst, dann nach Signal (stärkstes zuerst)."""
    groups: dict[tuple, list[dict]] = {}
    for d in devices:
        if address(d.get("address")):
            groups.setdefault(_key(d), []).append(d)
    out = [_row(g) for g in groups.values()]
    out.sort(key=lambda r: (not r["paired"], -(r["rssi"] if r["rssi"] is not None else -999), r["name"]))
    return out


def pair_order(devices: list[dict], addr: str) -> list[str]:
    """Adressen, die beim Koppeln von `addr` in dieser Reihenfolge versucht werden (seine Zeile, klassisch zuerst)."""
    for r in rows(devices):
        if addr in r["addresses"]:
            return list(r["addresses"])
    return []


def weak_signal(devices: list[dict]) -> bool:
    rssis = [d["rssi"] for d in devices if d.get("rssi") is not None]
    return bool(rssis) and max(rssis) < WEAK_DBM
