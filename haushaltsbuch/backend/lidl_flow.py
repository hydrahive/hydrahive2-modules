"""Strikte, verschlüsselte Hilfen für kurzlebige Lidl-PKCE-Flows."""
from __future__ import annotations

import base64
import hashlib
import json

from hydrahive.credentials._crypto import decrypt, encrypt
from hydrahive.settings import settings

_FIELDS = {
    "flow_id", "household_id", "member_id", "state", "nonce", "verifier", "expires_at",
}
_STRING_LIMITS = {
    "flow_id": (20, 200), "state": (20, 200), "nonce": (20, 200),
    "verifier": (43, 200), "expires_at": (10, 100),
}


class InvalidFlow(ValueError):
    pass


class AuthFlowError(RuntimeError):
    def __init__(self, code: str, status_code: int = 400):
        self.code, self.status_code = code, status_code
        super().__init__(code)


def pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def flow_hash(flow_id: str) -> str:
    return hashlib.sha256(flow_id.encode()).hexdigest()


def seal_flow(flow: dict) -> str:
    return encrypt(json.dumps(flow, separators=(",", ":")), settings.data_dir)


def read_flow(token: str) -> dict:
    if not isinstance(token, str) or not token.startswith("enc:v1:") or len(token) > 8000:
        raise InvalidFlow
    try:
        flow = json.loads(decrypt(token, settings.data_dir))
    except Exception as exc:
        raise InvalidFlow from exc
    if not isinstance(flow, dict) or set(flow) != _FIELDS:
        raise InvalidFlow
    for key, (minimum, maximum) in _STRING_LIMITS.items():
        value = flow.get(key)
        if not isinstance(value, str) or not minimum <= len(value) <= maximum:
            raise InvalidFlow
    for key in ("household_id", "member_id"):
        value = flow.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise InvalidFlow
    return flow
