"""Schranke für die Zuspielung an Liquidsoap: nur von 127.0.0.1 (direkt, nicht über nginx) und nur mit Feed-Schlüssel.

Der Schlüssel liegt in /etc/hydrahive2/radiostream/secrets.env (0600, von extension/install.sh erzeugt). Er wird bei
jedem Aufruf frisch gelesen (Update/Neuerzeugung ohne Neustart) und zeitkonstant verglichen. Er öffnet nur /feed/*.
"""
from __future__ import annotations

import hmac
from pathlib import Path

from fastapi import Request, status
from hydrahive.api.middleware.errors import coded

SECRETS_FILE = Path("/etc/hydrahive2/radiostream/secrets.env")
HEADER = "X-Radiostream-Feed"
_FORWARD = ("x-forwarded-for", "x-real-ip", "forwarded")


def read_secret(name: str) -> str:
    try:
        for line in SECRETS_FILE.read_text().splitlines():
            k, _, v = line.partition("=")
            if k.strip() == name:
                return v.strip()
    except OSError:
        pass
    return ""


def _client_host(request: Request) -> str:
    return request.client.host if request.client else ""


def require_feed(request: Request) -> None:
    key = read_secret("RADIOSTREAM_FEED_KEY")
    given = request.headers.get(HEADER, "")
    local = _client_host(request) in ("127.0.0.1", "::1", "testclient") and \
        not any(h in request.headers for h in _FORWARD)
    if not (key and local and hmac.compare_digest(given.encode(), key.encode())):
        raise coded(status.HTTP_403_FORBIDDEN, "radiostream_feed_forbidden")
