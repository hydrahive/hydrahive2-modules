from __future__ import annotations

from dataclasses import dataclass

from hydrahive.credentials.store import get_credential

from .config import MAX_CREDENTIAL_LENGTH, SAB_ALLOWED_ORIGIN, SAB_CREDENTIAL
from .errors import MediacenterConfigError
from .origins import canonical_origin


@dataclass(frozen=True)
class SabConnection:
    origin: str
    api_key: str


def resolve_sab_connection(username: str) -> SabConnection:
    """Loest Adresse + Schluessel der SABnzbd-Instanz auf.

    Die Adresse stammt aus dem `url_pattern` des Credentials. Ist
    `HH_MEDIACENTER_SAB_ORIGIN` gesetzt, muss sie damit uebereinstimmen — so
    kann ein Betreiber die erlaubte Adresse serverseitig festnageln, ohne dass
    im Code eine feste Adresse stehen muss.
    """
    credential = get_credential(username, SAB_CREDENTIAL)
    if credential is None:
        raise MediacenterConfigError("sab_not_configured")
    api_key = credential.value.strip()
    origin = canonical_origin(credential.url_pattern)
    if not api_key or len(api_key) > MAX_CREDENTIAL_LENGTH or origin is None:
        raise MediacenterConfigError("sab_not_configured")
    if SAB_ALLOWED_ORIGIN:
        allowed_origin = canonical_origin(SAB_ALLOWED_ORIGIN)
        if allowed_origin is None or origin != allowed_origin:
            raise MediacenterConfigError("sab_not_configured")
    return SabConnection(origin=origin, api_key=api_key)
