"""S7: Bluetooth aus Sicht des Backends – Stand vom Dienst lesen, Aufträge unter den Regeln der Spec ablegen.

Der Dienst (renderer/bt_service.py) spricht BlueZ an und schreibt bt/state.json; hier wird nur gelesen/geprüft.
Regeln (SPEC S7): Koppeln nur bei offenem Fenster und nur für Geräte, die die Suche gesehen hat; Entfernen nur für
gekoppelte Geräte; ein offenes Fenster wird nicht verlängert.
"""
from __future__ import annotations

import re
import time
from pathlib import Path

from renderer import bt_jobs, bt_model

STALE_SECONDS = 15          # Dienst schreibt alle 2 s; länger still → nicht verfügbar
_PASSKEY = re.compile(r"^\d{6}$")


class BtError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _fresh(data: Path, now: float) -> dict | None:
    s = bt_jobs.read_state(data)
    if not s or not isinstance(s.get("updated"), (int, float)) or now - s["updated"] > STALE_SECONDS:
        return None
    return s


def _devices(s: dict) -> list[dict]:
    return [d for d in (s.get("devices") or []) if isinstance(d, dict) and bt_model.address(d.get("address"))]


def _window_left(s: dict, now: float) -> int:
    until = s.get("window_until")
    return max(0, int(round(until - now))) if isinstance(until, (int, float)) else 0


def view(data: Path, *, now: float | None = None) -> dict:
    now = time.time() if now is None else now
    s = _fresh(data, now)
    if s is None:
        return {"available": False, "adapter": None, "window_left": 0, "devices": [], "weak_signal": False,
                "pairing": None, "error": None}
    devs = _devices(s)
    pairing = s.get("pairing") if isinstance(s.get("pairing"), dict) else None
    if pairing:
        code = str(pairing.get("passkey") or "")
        pairing = {"address": bt_model.address(pairing.get("address")),
                   "passkey": code if _PASSKEY.match(code) else None}
    adapter = s.get("adapter") if isinstance(s.get("adapter"), dict) else None
    return {
        "available": True,
        "adapter": {"name": str(adapter.get("name", ""))[:60], "powered": bool(adapter.get("powered"))} if adapter else None,
        "window_left": _window_left(s, now),
        "devices": bt_model.rows(devs),
        "weak_signal": bt_model.weak_signal(devs),
        "pairing": pairing,
        "error": str(s["error"])[:200] if s.get("error") else None,
    }


def scan(data: Path, *, now: float | None = None) -> dict:
    now = time.time() if now is None else now
    s = _fresh(data, now)
    if s is None:
        raise BtError("unavailable")
    if _window_left(s, now) > 0 or bt_jobs.pending(data, "scan"):
        return {"started": False}
    bt_jobs.put(data, "scan", now=now)
    return {"started": True}


def pair(data: Path, raw_address: object, *, now: float | None = None) -> None:
    now = time.time() if now is None else now
    addr = bt_model.address(raw_address)
    if addr is None:
        raise BtError("invalid_address")
    s = _fresh(data, now)
    if s is None:
        raise BtError("unavailable")
    if _window_left(s, now) <= 0:
        raise BtError("window_closed")
    if not bt_model.pair_order(_devices(s), addr):
        raise BtError("not_seen")
    bt_jobs.put(data, "pair", addr, now=now)


def remove(data: Path, raw_address: object, *, now: float | None = None) -> None:
    now = time.time() if now is None else now
    addr = bt_model.address(raw_address)
    if addr is None:
        raise BtError("invalid_address")
    s = _fresh(data, now)
    if s is None:
        raise BtError("unavailable")
    if not any(d["address"] == addr and d.get("paired") for d in _devices(s)):
        raise BtError("not_paired")
    bt_jobs.put(data, "remove", addr, now=now)
