"""HydraHive-App: Fingerabdruck des Server-Zertifikats (app_tls) – lang für die Technik, kurz zum Vergleichen."""
from __future__ import annotations

from backend import app_tls

M = "/api/modules/tvwerkstatt"


def test_pin_nur_fuer_lokale_adressen():
    assert app_tls.is_local("192.168.178.2") and app_tls.is_local("hydra.fritz.box") and app_tls.is_local("nas")
    assert not app_tls.is_local("hydra.example.com") and not app_tls.is_local("8.8.8.8")
    assert app_tls.pin_for("hydra.example.com") is None


def test_kurzer_fingerabdruck_wie_in_der_app():
    """Gleicher Prüfwert wie LogicTest.fingerabdruckKurzUndWieDerServer (SHA-256 von „abc“)."""
    import base64
    import hashlib
    pin = "sha256/" + base64.b64encode(hashlib.sha256(b"abc").digest()).decode()
    assert app_tls.short(pin) == "BA78 16BF 8F01"
    assert app_tls.short(None) is None and app_tls.short("sha256/kaputt") is None and app_tls.short("md5/x") is None
    assert app_tls.short("sha256/" + base64.b64encode(b"\x01" * 20).decode()) is None     # kein SHA-256


def test_fingerabdruck_aus_echtem_zertifikat(tmp_path):
    """Selbst ausgestelltes Zertifikat wie auf dem Server: Pin = SHA-256 über den öffentlichen Schlüssel (SPKI)."""
    import base64
    import datetime
    import hashlib

    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "hydrahive2")])
    now = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(1).not_valid_before(now).not_valid_after(now + datetime.timedelta(days=30))
            .sign(key, hashes.SHA256()))
    spki = key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    want = hashlib.sha256(spki).digest()
    pin = app_tls.spki_pin(cert.public_bytes(serialization.Encoding.PEM))
    assert pin == "sha256/" + base64.b64encode(want).decode()
    hexd = want.hex().upper()
    assert app_tls.short(pin) == f"{hexd[:4]} {hexd[4:8]} {hexd[8:12]}"


def test_code_liefert_kurzen_fingerabdruck(client, admin_headers, monkeypatch):
    monkeypatch.setattr(app_tls, "pin_for", lambda host: "sha256/" + "A" * 43 + "=")
    r = client.post(M + "/app/pairing", json={"name": "Flur"}, headers={**admin_headers, "Host": "192.0.2.1"})
    assert r.status_code == 201 and r.json()["pin_short"] == "0000 0000 0000"
