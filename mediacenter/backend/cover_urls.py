"""Validierung von Cover-/Backdrop-URLs aus dem Indexer.

Bewusst dieselbe strenge Linie wie `download_urls.safe_download_url`:

- nur https, kein Benutzer/Passwort, kein Fragment, Laengenlimit
- Host-Allowlist — der Indexer soll uns nicht auf beliebige Hosts zeigen lassen
- **Querywerte werden verworfen**: der Indexer spiegelt den API-Schluessel in
  anderen Feldern zurueck; ueber einen Queryparameter koennte er auch hier
  mitreisen. Der Pfad allein genuegt fuer ein Bild.
"""
from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

from .config import COVER_HOSTS

MAX_COVER_URL_LENGTH = 2048


def safe_cover_url(raw: str | None) -> str | None:
    """Gibt eine bereinigte Cover-URL zurueck oder None.

    Nie eine Ausnahme — ein kaputtes Cover darf niemals eine Suche scheitern
    lassen. Im Zweifel: kein Bild.
    """
    if not raw or len(raw) > MAX_COVER_URL_LENGTH:
        return None
    if any(character.isspace() for character in raw):
        return None
    try:
        parsed = urlsplit(raw)
        valid = (
            parsed.scheme == "https"
            and (parsed.hostname or '').lower() in COVER_HOSTS
            and parsed.port in {None, 443}
            and parsed.username is None
            and parsed.password is None
        )
    except ValueError:
        return None
    if not valid or not parsed.path.startswith("/") or parsed.fragment:
        return None
    return urlunsplit(("https", parsed.hostname, parsed.path, "", ""))
