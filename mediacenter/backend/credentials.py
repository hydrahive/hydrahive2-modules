from __future__ import annotations

from hydrahive.credentials.models import matches_url
from hydrahive.credentials.store import get_credential

from .config import (
    INDEXER_API_URL,
    INDEXER_CREDENTIAL,
    INDEXER_ORIGIN,
    MAX_CREDENTIAL_LENGTH,
)
from .errors import MediacenterConfigError


def resolve_indexer_api_key(username: str) -> str:
    """Lädt den benutzergebundenen Treasure-Maps-Key ohne ihn zu serialisieren."""
    credential = get_credential(username, INDEXER_CREDENTIAL)
    if credential is None:
        raise MediacenterConfigError("indexer_not_configured")
    value = credential.value.strip()
    if not value or len(value) > MAX_CREDENTIAL_LENGTH:
        raise MediacenterConfigError("indexer_not_configured")
    pattern = credential.url_pattern.rstrip("/")
    if pattern != INDEXER_ORIGIN and not matches_url(credential.url_pattern, INDEXER_API_URL):
        raise MediacenterConfigError("indexer_not_configured")
    return value
