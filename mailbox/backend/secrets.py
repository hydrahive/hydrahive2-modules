"""Zugangsdaten der Mailkonten verschlüsseln (Spec §3/§11).

AES-GCM mit einem **eigenen** Schlüssel, abgeleitet (HKDF) aus dem Master-Schlüssel des Kerns
(credentials/_crypto). Die Konto-ID ist als zusätzliche Authentifizierung gebunden: Ein Geheimnis von Konto A lässt
sich nicht als Geheimnis von Konto B öffnen. Klartext wird nie durchgelassen (anders als der Kern bei Altbeständen).
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

PREFIX = "mbx:v1:"
_NONCE = 12


class SecretError(ValueError):
    """Geheimnis fehlt, ist kaputt, verändert oder gehört zu einem anderen Konto."""


def _key() -> bytes:
    master = _crypto._load_key(settings.data_dir)
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"hydrahive-mailbox-v1").derive(master)


def _aad(account_id: str) -> bytes:
    return b"mailbox:" + account_id.encode()


def seal(account_id: str, plaintext: str) -> str:
    nonce = os.urandom(_NONCE)
    ct = AESGCM(_key()).encrypt(nonce, plaintext.encode(), _aad(account_id))
    return PREFIX + base64.urlsafe_b64encode(nonce + ct).decode()


def open_(account_id: str, value: str) -> str:
    if not isinstance(value, str) or not value.startswith(PREFIX):
        raise SecretError("kein verschlüsseltes Mailbox-Geheimnis")
    try:
        raw = base64.urlsafe_b64decode(value[len(PREFIX):] + "==")
    except (binascii.Error, ValueError) as e:
        raise SecretError("Geheimnis kaputt") from e
    if len(raw) <= _NONCE + 16:
        raise SecretError("Geheimnis kaputt")
    try:
        return AESGCM(_key()).decrypt(raw[:_NONCE], raw[_NONCE:], _aad(account_id)).decode()
    except (InvalidTag, UnicodeDecodeError) as e:
        raise SecretError("Geheimnis passt nicht zu diesem Konto") from e
