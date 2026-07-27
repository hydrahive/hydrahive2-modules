"""Radarr/Sonarr: Adresse + Schluessel aus EINER Quelle.

Die Adresse steht im `url_pattern` des Credentials — dort pflegt der Nutzer sie
ohnehin, wenn er den Schluessel eintraegt. Eine Umgebungsvariable
(`HH_MEDIACENTER_RADARR_ORIGIN`) ist optional und wirkt nur als Einschraenkung:
ist sie gesetzt, muss das Credential dazu passen. Ohne sie genuegt das
Credential allein.

Damit gibt es keine zwei Orte fuer dieselbe Information.
"""
from __future__ import annotations

from dataclasses import dataclass

from hydrahive.credentials.store import get_credential

from .config import (
    MAX_CREDENTIAL_LENGTH,
    RADARR_CREDENTIAL,
    RADARR_ORIGIN,
    SONARR_CREDENTIAL,
    SONARR_ORIGIN,
)
from .errors import MediacenterConfigError
from .origins import canonical_origin

# Nur diese Dienste sind ansprechbar — kein frei waehlbarer Name.
ARR_SERVICES = ("radarr", "sonarr")


@dataclass(frozen=True)
class ArrConnection:
    service: str
    origin: str
    api_key: str


def _settings(service: str) -> tuple[str, str]:
    if service == "radarr":
        return RADARR_CREDENTIAL, RADARR_ORIGIN
    if service == "sonarr":
        return SONARR_CREDENTIAL, SONARR_ORIGIN
    raise ValueError(f"Unbekannter Dienst: {service!r}")


def resolve_arr_connection(username: str, service: str) -> ArrConnection:
    """Loest Adresse und Schluessel auf. Raises MediacenterConfigError."""
    credential_name, allowed_origin_raw = _settings(service)
    code = f"{service}_not_configured"

    credential = get_credential(username, credential_name)
    if credential is None:
        raise MediacenterConfigError(code)
    api_key = credential.value.strip()
    origin = canonical_origin(credential.url_pattern)
    if not api_key or len(api_key) > MAX_CREDENTIAL_LENGTH or origin is None:
        raise MediacenterConfigError(code)
    if allowed_origin_raw:
        allowed = canonical_origin(allowed_origin_raw)
        if allowed is None or origin != allowed:
            raise MediacenterConfigError(code)
    return ArrConnection(service=service, origin=origin, api_key=api_key)


def is_configured(username: str, service: str) -> bool:
    """True, wenn der Dienst nutzbar ist. Wirft nie."""
    try:
        resolve_arr_connection(username, service)
    except (MediacenterConfigError, ValueError):
        return False
    return True
