"""Zugänge aus dem Safe des Admins, der das Modul eingerichtet hat. Hier wird nur gelesen, nie gespeichert."""
from __future__ import annotations

from hydrahive.credentials.store import get_credential, list_credentials

from .errors import NetError

KEY_TYPES = ("bearer", "header", "query")


def udm_key(owner: str, name: str | None) -> str:
    """API-Schlüssel der Dream Machine. Der Typ im Safe ist egal (Till hat „bearer“) – das Modul sendet ihn immer
    als X-API-KEY (gemessen 01.11.: nur so akzeptiert)."""
    cred = get_credential(owner, name) if name else None
    if cred is None or cred.type not in KEY_TYPES or not cred.value:
        raise NetError("network_credential_invalid")
    return cred.value


def fritz_login(owner: str, name: str | None) -> tuple[str, str]:
    cred = get_credential(owner, name) if name else None
    if cred is None or cred.type != "basic":
        raise NetError("network_credential_invalid")
    user, _, password = cred.value.partition(":")
    return user, password


def names(owner: str) -> list[dict]:
    """Nur Name, Art und Adressmuster für die Auswahl – nie der Wert."""
    return [{"name": c.name, "type": c.type, "url_pattern": c.url_pattern}
            for c in list_credentials(owner) if c.type in (*KEY_TYPES, "basic")]
