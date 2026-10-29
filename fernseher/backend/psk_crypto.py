"""Schlüssel des Fernsehers verschlüsseln (SPEC.md „Einstellungen“). Muster: telephony/backend/secrets.py.

AES-GCM mit einem eigenen Schlüssel, abgeleitet (HKDF) aus dem Master-Schlüssel des Kerns. Klartext wird nie
gespeichert und nie zurückgegeben; Fehlertexte enthalten den Wert nicht.
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

PREFIX = "tv:v1:"
_NONCE = 12
_AAD = b"fernseher:psk"


class SecretError(ValueError):
    """Schlüssel fehlt, ist kaputt oder verändert."""


def _key() -> bytes:
    master = _crypto._load_key(settings.data_dir)
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"hydrahive-fernseher-v1").derive(master)


def seal(plaintext: str) -> str:
    nonce = os.urandom(_NONCE)
    ct = AESGCM(_key()).encrypt(nonce, plaintext.encode(), _AAD)
    return PREFIX + base64.urlsafe_b64encode(nonce + ct).decode()


def open_(value: str) -> str:
    if not isinstance(value, str) or not value.startswith(PREFIX):
        raise SecretError("kein verschlüsselter Schlüssel")
    try:
        raw = base64.urlsafe_b64decode(value[len(PREFIX):] + "==")
    except (binascii.Error, ValueError) as e:
        raise SecretError("Schlüssel kaputt") from e
    if len(raw) <= _NONCE + 16:
        raise SecretError("Schlüssel kaputt")
    try:
        return AESGCM(_key()).decrypt(raw[:_NONCE], raw[_NONCE:], _AAD).decode()
    except (InvalidTag, UnicodeDecodeError) as e:
        raise SecretError("Schlüssel verändert") from e
