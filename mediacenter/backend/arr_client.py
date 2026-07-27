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


# --- Lookup / Anlegen / Release uebergeben ---------------------------------
#
# Ab hier schreibende Aufrufe. Sie werden ausschliesslich durch eine
# ausdrueckliche Nutzeraktion ausgeloest — kein Agent-Tool greift darauf zu
# (siehe SPEC-V3.md, E5 folgt mit Bestaetigungsgate).

_PATHS = {
    "radarr": {"lookup": "/api/v3/movie/lookup", "add": "/api/v3/movie",
               "list": "/api/v3/movie"},
    "sonarr": {"lookup": "/api/v3/series/lookup", "add": "/api/v3/series",
               "list": "/api/v3/series"},
}


async def _request(connection: ArrConnection, method: str, path: str,
                   *, params: dict | None = None, json_body: dict | None = None):
    """Ein Aufruf gegen den Zieldienst. Raises IndexerResponseError."""
    from .errors import IndexerResponseError

    url = f"{connection.origin}{path}"
    try:
        async with httpx.AsyncClient(timeout=ARR_TIMEOUT_SECONDS) as client:
            response = await client.request(
                method, url, params=params, json=json_body,
                headers={"X-Api-Key": connection.api_key},
            )
    except httpx.HTTPError as exc:
        logger.warning("%s nicht erreichbar: %s", connection.service, type(exc).__name__)
        raise IndexerResponseError(f"{connection.service}_unreachable") from None
    if response.status_code == 401:
        raise IndexerResponseError(f"{connection.service}_unauthorized")
    if response.status_code >= 400:
        # Fehlertext des Dienstes NICHT durchreichen: er kann die aufgerufene
        # URL enthalten und damit in Randfaellen Parameter offenlegen.
        logger.warning("%s HTTP %s auf %s", connection.service, response.status_code, path)
        raise IndexerResponseError(f"{connection.service}_rejected")
    if not response.content:
        return None
    try:
        return response.json()
    except ValueError:
        raise IndexerResponseError(f"{connection.service}_invalid_response") from None


async def lookup(connection: ArrConnection, *, imdb_id: str | None = None,
                 tvdb_id: str | None = None, term: str | None = None) -> dict | None:
    """Sucht einen Titel im Katalog des Zieldienstes (TMDB/TVDB)."""
    if imdb_id:
        query = f"imdb:tt{imdb_id.lstrip('t')}"
    elif tvdb_id:
        query = f"tvdb:{tvdb_id}"
    elif term:
        query = term
    else:
        return None
    data = await _request(connection, "GET", _PATHS[connection.service]["lookup"],
                          params={"term": query})
    if isinstance(data, list) and data:
        return data[0] if isinstance(data[0], dict) else None
    return data if isinstance(data, dict) else None


async def add_title(connection: ArrConnection, payload: dict) -> dict:
    """Legt einen Titel in der Bibliothek an."""
    data = await _request(connection, "POST", _PATHS[connection.service]["add"],
                          json_body=payload)
    return data if isinstance(data, dict) else {}


async def push_release(connection: ArrConnection, guid: str, indexer_id: int) -> bool:
    """Uebergibt ein Release zum Download an den Zieldienst."""
    await _request(connection, "POST", "/api/v3/release",
                   json_body={"guid": guid, "indexerId": indexer_id})
    return True


async def default_indexer_id(connection: ArrConnection) -> int | None:
    """Erster aktiver Indexer des Dienstes — der Treffer stammt aus demselben."""
    data = await _request(connection, "GET", "/api/v3/indexer")
    if not isinstance(data, list):
        return None
    for entry in data:
        if isinstance(entry, dict) and entry.get("id"):
            return int(entry["id"])
    return None


async def quality_profiles(connection: ArrConnection) -> list[dict]:
    data = await _request(connection, "GET", "/api/v3/qualityprofile")
    return [{"id": p["id"], "name": str(p.get("name", ""))[:64]}
            for p in data or [] if isinstance(p, dict) and p.get("id")]


async def root_folders(connection: ArrConnection) -> list[dict]:
    data = await _request(connection, "GET", "/api/v3/rootfolder")
    return [{"id": f.get("id"), "path": str(f.get("path", ""))[:256],
             "free_space": f.get("freeSpace")}
            for f in data or [] if isinstance(f, dict) and f.get("path")]
