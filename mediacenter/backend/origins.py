"""Kanonisierung von Dienst-Adressen (Origins).

Gemeinsame Grundlage fuer SABnzbd, Radarr und Sonarr: alle drei bekommen ihre
Adresse aus dem `url_pattern` eines Credentials und muessen sie identisch
streng pruefen. Vorher lag diese Logik nur in `sab_credentials` — bei einem
zweiten Aufrufer waere sie kopiert worden.
"""
from __future__ import annotations

import re
from urllib.parse import urlsplit, urlunsplit

_HOSTNAME = re.compile(r"[A-Za-z0-9.:-]{1,253}")


def canonical_origin(pattern: str) -> str | None:
    """Normalisiert 'http://Host:Port/' auf 'http://host:port'.

    None bei allem, was kein blankes Origin ist: fremdes Schema, Benutzer/
    Passwort, Pfad, Query oder Fragment. Ein Wildcard-Pattern ('*') ist damit
    ebenfalls ungueltig — eine Adresse muss eindeutig sein.
    """
    try:
        parsed = urlsplit((pattern or "").strip())
        port = parsed.port
    except ValueError:
        return None
    hostname = parsed.hostname
    if (
        parsed.scheme not in {"http", "https"}
        or not hostname
        or not _HOSTNAME.fullmatch(hostname)
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        return None
    default_port = 80 if parsed.scheme == "http" else 443
    host = f"[{hostname}]" if ":" in hostname else hostname.lower().rstrip(".")
    netloc = host if port in {None, default_port} else f"{host}:{port}"
    return urlunsplit((parsed.scheme, netloc, "", "", ""))
