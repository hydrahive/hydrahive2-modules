"""Energie-Quellen für die Energie-Steuerung (Spec §E5).

Eine Quelle liefert nur eins: ``available_watts() -> float | None``.
``None`` heißt „Quelle gerade nicht erreichbar“. Neue Quellen (Home Assistant,
MQTT, eigener PV-Eigenbau …) kommen als weitere Klasse hinzu — sonst ändert
sich nichts. Abgerufen wird im Hintergrundjob, nicht pro Rig-Meldung.
"""
from __future__ import annotations

import ipaddress
import logging
from typing import Protocol
from urllib.parse import urlsplit

import httpx

logger = logging.getLogger(__name__)


class PowerSource(Protocol):
    def available_watts(self) -> float | None: ...


class FixedSource:
    """Fester Wert, z. B. „höchstens 2000 W“ — zum Testen und als Notlösung."""

    def __init__(self, watts: float) -> None:
        self.watts = max(0.0, float(watts))

    def available_watts(self) -> float | None:
        return self.watts


def _json_path(data, path: str):
    for part in [p for p in path.split(".") if p]:
        if isinstance(data, list) and part.isdigit():
            data = data[int(part)] if int(part) < len(data) else None
        elif isinstance(data, dict):
            data = data.get(part)
        else:
            return None
    return data


def validate_url(url: str) -> str:
    """Nur http(s) ins lokale Netz: die PV-Anlage hängt im LAN, nicht im Internet."""
    u = urlsplit(url or "")
    if u.scheme not in ("http", "https") or not u.hostname or u.username or u.password:
        raise ValueError("power_url_invalid")
    try:
        ip = ipaddress.ip_address(u.hostname)
    except ValueError:
        if not (u.hostname.endswith(".local") or u.hostname.endswith(".lan") or "." not in u.hostname):
            raise ValueError("power_url_must_be_lan") from None
        return url
    if not (ip.is_private and not ip.is_loopback and not ip.is_link_local):
        raise ValueError("power_url_must_be_lan")
    return url


class HttpJsonSource:
    """GET auf eine URL im LAN, Zahl aus einem JSON-Feld (z. B. ``data.surplus_w``)."""

    def __init__(self, url: str, field: str, *, scale: float = 1.0, timeout: float = 5.0) -> None:
        self.url, self.field, self.scale, self.timeout = validate_url(url), field, scale, timeout

    def available_watts(self) -> float | None:
        try:
            r = httpx.get(self.url, timeout=self.timeout, follow_redirects=False)
            r.raise_for_status()
            v = _json_path(r.json(), self.field)
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Mining: Energie-Quelle nicht lesbar: %s", exc)
            return None
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            return None
        return max(0.0, float(v) * self.scale)


def from_config(cfg: dict) -> PowerSource | None:
    mode = cfg.get("power_mode", "off")
    if mode == "fixed":
        return FixedSource(cfg.get("power_fixed_w", 0))
    if mode == "http":
        return HttpJsonSource(cfg.get("power_url", ""), cfg.get("power_field", ""),
                              scale=cfg.get("power_scale", 1.0))
    return None
