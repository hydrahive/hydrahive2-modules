"""Kennwort der SIP-Verbindung verschlüsselt (PLAN-EINSTELLUNGEN, SPEC-V1 §2.12)."""
from __future__ import annotations

import pytest


def test_roundtrip_und_kein_klartext() -> None:
    from backend import secrets

    sealed = secrets.seal("conn-a", "Geheim-Kennwort-123")
    assert sealed.startswith("tel:v1:")
    assert "Geheim" not in sealed
    assert secrets.open_("conn-a", sealed) == "Geheim-Kennwort-123"


def test_jedes_mal_anders_verschluesselt() -> None:
    from backend import secrets

    assert secrets.seal("conn-a", "x" * 12) != secrets.seal("conn-a", "x" * 12)


def test_falsche_verbindung_kann_nicht_oeffnen() -> None:
    from backend import secrets

    sealed = secrets.seal("conn-a", "Geheim-Kennwort-123")
    with pytest.raises(secrets.SecretError):
        secrets.open_("conn-b", sealed)


@pytest.mark.parametrize("value", ["", "Geheim-Kennwort-123", "tel:v1:", "tel:v1:!!!", "mbx:v1:abcd"])
def test_klartext_und_kaputtes_wird_abgelehnt(value: str) -> None:
    from backend import secrets

    with pytest.raises(secrets.SecretError):
        secrets.open_("conn-a", value)


def test_veraenderter_inhalt_wird_erkannt() -> None:
    from backend import secrets

    sealed = secrets.seal("conn-a", "Geheim-Kennwort-123")
    body = sealed[len("tel:v1:"):]
    flipped = body[:-3] + ("A" if body[-3] != "A" else "B") + body[-2:]
    with pytest.raises(secrets.SecretError):
        secrets.open_("conn-a", "tel:v1:" + flipped)


def test_eigener_schluessel_nicht_der_der_mailbox() -> None:
    """Ein Geheimnis eines anderen Moduls mit derselben ID lässt sich nicht öffnen (eigener HKDF-Zweck)."""
    import base64
    import os

    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from hydrahive.credentials import _crypto
    from hydrahive.settings import settings

    from backend import secrets

    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF

    master = _crypto._load_key(settings.data_dir)
    mailbox_key = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"hydrahive-mailbox-v1").derive(master)
    nonce = os.urandom(12)
    ct = AESGCM(mailbox_key).encrypt(nonce, b"Geheim-Kennwort-123", b"telephony:conn-a")
    with pytest.raises(secrets.SecretError):
        secrets.open_("conn-a", "tel:v1:" + base64.urlsafe_b64encode(nonce + ct).decode())
