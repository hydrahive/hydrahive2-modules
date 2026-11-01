"""Nur Geräte im eigenen Heimnetz: private Adressen oder Heimnetz-Namen. Kein Internet, kein localhost."""
from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlsplit

from .errors import NetError

LOCAL_SUFFIXES = (".local", ".lan", ".home", ".internal", ".box", ".home.arpa", ".localdomain")
_NAME = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)*$")


def local_host(host: str) -> str:
    h = (host or "").strip().lower()
    try:
        a = ipaddress.ip_address(h)
    except ValueError:
        if _NAME.match(h) and h.endswith(LOCAL_SUFFIXES):
            return h
        raise NetError("network_host_not_local") from None
    if a.is_private and not (a.is_loopback or a.is_link_local or a.is_unspecified):
        return h
    raise NetError("network_host_not_local")


def udm_url(url: str) -> tuple[str, int]:
    try:
        u = urlsplit((url or "").strip())
        port = u.port or 443
    except ValueError:
        raise NetError("network_url_invalid") from None
    if u.scheme != "https" or not u.hostname or u.username or u.path not in ("", "/") or u.query or u.fragment:
        raise NetError("network_url_invalid")
    return local_host(u.hostname), port
