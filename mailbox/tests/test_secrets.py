"""M1 Schritt 2: Passwörter verschlüsselt, an das Konto gebunden, nie Klartext durchgelassen."""
from __future__ import annotations

import pytest


def test_rundum_und_kein_klartext():
    from backend import secrets
    enc = secrets.seal("a1", "geheim-Passwort-ä")
    assert enc.startswith("mbx:v1:") and "geheim" not in enc
    assert secrets.open_("a1", enc) == "geheim-Passwort-ä"


def test_jedes_mal_anders():
    from backend import secrets
    assert secrets.seal("a1", "x") != secrets.seal("a1", "x")


def test_an_konto_gebunden():
    """Ein Geheimnis von Konto a1 lässt sich nicht als Geheimnis von a2 öffnen (kein Vertauschen in der DB)."""
    from backend import secrets
    enc = secrets.seal("a1", "pw")
    with pytest.raises(secrets.SecretError):
        secrets.open_("a2", enc)


@pytest.mark.parametrize("bad", ["klartext", "", "enc:v1:abc", "mbx:v1:", "mbx:v1:!!!", "mbx:v1:QUJD"])
def test_klartext_oder_kaputt_wird_abgelehnt(bad):
    from backend import secrets
    with pytest.raises(secrets.SecretError):
        secrets.open_("a1", bad)


def test_veraendert_wird_abgelehnt():
    from backend import secrets
    enc = secrets.seal("a1", "pw")
    flipped = enc[:-3] + ("A" if enc[-3] != "A" else "B") + enc[-2:]
    with pytest.raises(secrets.SecretError):
        secrets.open_("a1", flipped)


def test_eigener_schluessel_nicht_der_kern_schluessel():
    """Mit dem Kern-Schlüssel direkt (ohne Ableitung) lässt sich ein Mailbox-Geheimnis nicht öffnen."""
    import base64

    from backend import secrets
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from hydrahive.credentials import _crypto
    from hydrahive.settings import settings
    raw = base64.urlsafe_b64decode(secrets.seal("a1", "pw")[len("mbx:v1:"):] + "==")
    with pytest.raises(InvalidTag):
        AESGCM(_crypto._load_key(settings.data_dir)).decrypt(raw[:12], raw[12:], b"mailbox:a1")
