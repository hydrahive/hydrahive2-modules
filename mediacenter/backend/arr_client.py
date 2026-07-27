"""Minimaler Radarr/Sonarr-Client — vorerst nur lesend.

Beide Dienste sprechen dieselbe API-Familie (`/api/v3`) und authentifizieren per
`X-Api-Key`-Header. Fuer die Einstellungsseite genuegt der Status-Endpunkt:
er beantwortet die Frage "erreichbar und Schluessel korrekt?".

Schreibende Aufrufe (Filme/Serien hinzufuegen) bewusst NICHT enthalten — die
brauchen erst ein Bestaetigungskonzept, damit ein Agent nicht ungefragt eine
Bibliothek umbaut.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from .arr_credentials import ArrConnection
from .errors import MediacenterConfigError

logger = logging.getLogger(__name__)

ARR_TIMEOUT_SECONDS = 10.0
MAX_JSON_BYTES = 256 * 1024


@dataclass(frozen=True)
class ArrStatus:
    service: str
    reachable: bool
    version: str | None = None
    app_name: str | None = None
    error: str | None = None


async def fetch_status(connection: ArrConnection) -> ArrStatus:
    """Fragt /api/v3/system/status ab. Wirft nie — Fehler landen im Ergebnis.

    Begruendung: ein nicht erreichbarer Zusatzdienst darf die
    Einstellungsseite nicht sprengen. Der Nutzer soll sehen, WAS klemmt.
    """
    url = f"{connection.origin}/api/v3/system/status"
    try:
        async with httpx.AsyncClient(timeout=ARR_TIMEOUT_SECONDS) as client:
            response = await client.get(url, headers={"X-Api-Key": connection.api_key})
            if response.status_code == 401:
                return ArrStatus(connection.service, False, error="unauthorized")
            if response.status_code >= 400:
                return ArrStatus(connection.service, False, error=f"http_{response.status_code}")
            if len(response.content) > MAX_JSON_BYTES:
                return ArrStatus(connection.service, False, error="response_too_large")
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        # Fehlertext bewusst nicht durchreichen: er koennte die URL und damit
        # in Randfaellen Query-Werte enthalten.
        logger.warning("%s nicht erreichbar: %s", connection.service, type(exc).__name__)
        return ArrStatus(connection.service, False, error="unreachable")

    if not isinstance(data, dict):
        return ArrStatus(connection.service, False, error="invalid_response")
    version = str(data.get("version") or "")[:32] or None
    app_name = str(data.get("appName") or "")[:32] or None
    return ArrStatus(connection.service, True, version=version, app_name=app_name)


async def status_for(username: str, service: str) -> ArrStatus:
    """Status eines Dienstes; nicht konfiguriert ist kein Fehler."""
    from .arr_credentials import resolve_arr_connection
    try:
        connection = resolve_arr_connection(username, service)
    except MediacenterConfigError:
        return ArrStatus(service, False, error="not_configured")
    return await fetch_status(connection)
