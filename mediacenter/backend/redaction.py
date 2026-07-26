from __future__ import annotations

from urllib.parse import unquote

from .models import RawRelease


def release_contains_secret(release: RawRelease, secret: str) -> bool:
    values = (
        release.title,
        release.guid,
        release.language or "",
        release.download_url or "",
    )
    for value in values:
        decoded = value
        while True:
            if secret in decoded:
                return True
            next_value = unquote(decoded)
            if next_value == decoded:
                break
            decoded = next_value
    return False
