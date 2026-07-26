from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def safe_download_url(raw: str) -> str | None:
    if not raw or len(raw) > 2048 or any(character.isspace() for character in raw):
        return None
    try:
        parsed = urlsplit(raw)
        valid_origin = (
            parsed.scheme == "https"
            and parsed.hostname == "treasure-maps.com"
            and parsed.port in {None, 443}
            and parsed.username is None
            and parsed.password is None
        )
    except ValueError:
        return None
    if not valid_origin or not parsed.path.startswith("/") or parsed.fragment:
        return None
    safe_query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in {"apikey", "api_key", "token"}
    ]
    return urlunsplit(
        ("https", "treasure-maps.com", parsed.path, urlencode(safe_query), "")
    )
