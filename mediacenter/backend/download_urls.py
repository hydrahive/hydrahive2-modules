from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

from .config import INDEXER_FILE_HOST, INDEXER_HOST


def safe_download_url(raw: str) -> str | None:
    if not raw or len(raw) > 2048 or any(character.isspace() for character in raw):
        return None
    try:
        parsed = urlsplit(raw)
        valid_origin = (
            parsed.scheme == "https"
            and (parsed.hostname or "").lower() in {INDEXER_HOST, INDEXER_FILE_HOST}
            and parsed.port in {None, 443}
            and parsed.username is None
            and parsed.password is None
        )
    except ValueError:
        return None
    if not valid_origin or not parsed.path.startswith("/") or parsed.fragment:
        return None
    # Die Referenz dient nur der Herkunftsvalidierung. Der NZB-Abruf nutzt
    # serverseitig GUID + API-Origin; sämtliche Upstream-Querywerte werden verworfen.
    return urlunsplit(("https", parsed.hostname, parsed.path, "", ""))
