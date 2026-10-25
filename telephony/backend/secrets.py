"""Kennwort der SIP-Verbindung verschlüsseln (SPEC-V1 §2.12, §16.4).

AES-GCM mit einem eigenen Schlüssel, abgeleitet (HKDF) aus dem Master-Schlüssel des Kerns. Die Verbindungs-ID ist als
zusätzliche Authentifizierung gebunden: Das Kennwort einer Verbindung lässt sich nicht als das einer anderen öffnen.
Klartext wird nie angenommen.
"""
from __future__ import annotations

import base64
import binascii
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from hydrahive.credentials import _crypto
from hydrahive.settings import settings

PREFIX = "tel:v1:"
_NONCE = 12


class SecretError(ValueError):
    """Kennwort fehlt, ist kaputt, verändert oder gehört zu einer anderen Verbindung."""


def _key() -> bytes:
    master = _crypto._load_key(settings.data_dir)
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"hydrahive-telephony-v1").derive(master)


def _aad(connection_id: str) -> bytes:
    return b"telephony:" + connection_id.encode()


def seal(connection_id: str, plaintext: str) -> str:
    nonce = os.urandom(_NONCE)
    ct = AESGCM(_key()).encrypt(nonce, plaintext.encode(), _aad(connection_id))
    return PREFIX + base64.urlsafe_b64encode(nonce + ct).decode()


def open_(connection_id: str, value: str) -> str:
    if not isinstance(value, str) or not value.startswith(PREFIX):
        raise SecretError("kein verschlüsseltes Telefonie-Kennwort")
    try:
        raw = base64.urlsafe_b64decode(value[len(PREFIX):] + "==")
    except (binascii.Error, ValueError) as e:
        raise SecretError("Kennwort kaputt") from e
    if len(raw) <= _NONCE + 16:
        raise SecretError("Kennwort kaputt")
    try:
        return AESGCM(_key()).decrypt(raw[:_NONCE], raw[_NONCE:], _aad(connection_id)).decode()
    except (InvalidTag, UnicodeDecodeError) as e:
        raise SecretError("Kennwort passt nicht zu dieser Verbindung") from e
