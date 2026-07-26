from __future__ import annotations

from urllib.parse import unquote

from .models import RawRelease


def text_contains_secret(value: str, secret: str) -> bool:
    decoded = value
    while True:
        if secret in decoded:
            return True
        next_value = unquote(decoded)
        if next_value == decoded:
            return False
        decoded = next_value


def release_contains_secret(release: RawRelease, secret: str) -> bool:
    values = (
        release.title,
        release.guid,
        release.language or "",
        release.download_url or "",
    )
    return any(text_contains_secret(value, secret) for value in values)
