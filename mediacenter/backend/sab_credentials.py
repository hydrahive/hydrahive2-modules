from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

from hydrahive.credentials.store import get_credential

from .config import MAX_CREDENTIAL_LENGTH, SAB_ALLOWED_ORIGIN, SAB_CREDENTIAL
from .errors import MediacenterConfigError


@dataclass(frozen=True)
class SabConnection:
    origin: str
    api_key: str


def _canonical_origin(pattern: str) -> str | None:
    try:
        parsed = urlsplit(pattern.strip())
        port = parsed.port
    except ValueError:
        return None
    hostname = parsed.hostname
    if (
        parsed.scheme not in {"http", "https"}
        or not hostname
        or not re.fullmatch(r"[A-Za-z0-9.:-]{1,253}", hostname)
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        return None
    default_port = 80 if parsed.scheme == "http" else 443
    host = f"[{hostname}]" if ":" in hostname else hostname.lower().rstrip(".")
    netloc = host if port in {None, default_port} else f"{host}:{port}"
    return urlunsplit((parsed.scheme, netloc, "", "", ""))


def resolve_sab_connection(username: str) -> SabConnection:
    credential = get_credential(username, SAB_CREDENTIAL)
    if credential is None:
        raise MediacenterConfigError("sab_not_configured")
    api_key = credential.value.strip()
    origin = _canonical_origin(credential.url_pattern)
    allowed_origin = _canonical_origin(SAB_ALLOWED_ORIGIN)
    if (
        not api_key
        or len(api_key) > MAX_CREDENTIAL_LENGTH
        or origin is None
        or origin != allowed_origin
    ):
        raise MediacenterConfigError("sab_not_configured")
    return SabConnection(origin=origin, api_key=api_key)
