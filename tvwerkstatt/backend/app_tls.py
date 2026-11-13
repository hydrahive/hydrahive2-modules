"""Fingerabdruck des Server-Zertifikats für die App (Muster: Modul mining, tls_pin.py).

Im Heimnetz nutzt HydraHive ein selbst ausgestelltes Zertifikat (config_dir/tls/hydrahive.crt). Es nennt oft nicht die
Adresse, unter der der Server erreichbar ist (hier: SAN 127.0.0.1 und .226, erreichbar unter .2). Die App prüft deshalb
nicht den Namen, sondern genau diesen öffentlichen Schlüssel (SPKI, SHA-256). Den Pin gibt es nur für lokale Adressen:
hinter einem öffentlichen Namen sitzt oft ein Proxy mit anderem Schlüssel – dort prüft die App wie üblich.
"""
from __future__ import annotations

import base64
import hashlib
import ipaddress
import logging

from hydrahive.settings import settings

logger = logging.getLogger(__name__)
LOCAL_SUFFIXES = (".local", ".lan", ".home", ".internal", ".localdomain", ".home.arpa", ".fritz.box")


def spki_pin(pem: bytes) -> str | None:
    try:
        from cryptography import x509
        from cryptography.hazmat.primitives import serialization
        key = x509.load_pem_x509_certificate(pem).public_key()
        spki = key.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    except (ValueError, TypeError) as exc:
        logger.warning("TV-Werkstatt: Server-Zertifikat nicht lesbar: %s", exc)
        return None
    return "sha256/" + base64.b64encode(hashlib.sha256(spki).digest()).decode("ascii")


def is_local(host: str) -> bool:
    h = (host or "").strip().lower().rstrip(".")
    if h.startswith("[") and "]" in h:
        h = h[1:h.index("]")]
    elif h.count(":") == 1:
        h = h.split(":", 1)[0]
    try:
        return ipaddress.ip_address(h).is_private
    except ValueError:
        return bool(h) and ("." not in h or h.endswith(LOCAL_SUFFIXES))


def pin_for(host: str) -> str | None:
    if not is_local(host):
        return None
    try:
        return spki_pin((settings.config_dir / "tls" / "hydrahive.crt").read_bytes())
    except OSError:
        return None


def short(pin: str | None) -> str | None:
    """Kurzform zum Vergleichen am Gerät: erste 12 Hex-Zeichen des Hashes, groß, in Vierergruppen (wie Logic.shortPin)."""
    if not pin or not pin.startswith("sha256/"):
        return None
    try:
        raw = base64.b64decode(pin[7:], validate=True)
    except ValueError:
        return None
    if len(raw) != 32:
        return None
    h = raw.hex()[:12].upper()
    return f"{h[:4]} {h[4:8]} {h[8:12]}"
