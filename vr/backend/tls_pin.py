"""Fingerabdruck des Server-Zertifikats für den Kopplungs-QR (Kopie aus mining/backend/tls_pin.py, Module sind eigenständig).

HydraHive-Installationen nutzen im Heimnetz meist ein selbst ausgestelltes
Zertifikat (installer/modules/60-nginx.sh → <config_dir>/tls/hydrahive.crt).
Die Brille vertraut dann genau diesem Zertifikat (Pinning).

Aber: Wird der Server über eine öffentliche Domain erreicht, sitzt davor oft
ein Proxy (Cloudflare & Co.) mit einem ECHTEN Zertifikat. Dessen Schlüssel ist
ein anderer als der lokale → ein Pin würde jede Verbindung ablehnen
(Fehler beim Kollegen am 03.10.2026: ``server_pin_mismatch`` über
hydra.myemployeeai.com). Deshalb gibt es den Pin nur, wenn die Brille den Server
über eine IP-Adresse oder einen Heimnetz-Namen anspricht. Sonst prüft die Brille
ganz normal gegen die System-CAs.
"""
from __future__ import annotations

import base64
import hashlib
import ipaddress
import logging
from pathlib import Path

from hydrahive.settings import settings

logger = logging.getLogger(__name__)
LOCAL_SUFFIXES = (".local", ".lan", ".home", ".internal", ".localdomain", ".home.arpa")


def _cert_path() -> Path:
    return settings.config_dir / "tls" / "hydrahive.crt"


def spki_pin_from_pem(pem: bytes) -> str | None:
    """curl-Format ``sha256//<base64>`` über den öffentlichen Schlüssel (SPKI)."""
    try:
        from cryptography import x509
        from cryptography.hazmat.primitives import serialization
        cert = x509.load_pem_x509_certificate(pem)
        spki = cert.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    except (ValueError, TypeError) as exc:
        logger.warning("VR: Server-Zertifikat nicht lesbar: %s", exc)
        return None
    return "sha256//" + base64.b64encode(hashlib.sha256(spki).digest()).decode("ascii")


def is_local_host(host: str) -> bool:
    """IP-Adresse, Name ohne Punkt oder Heimnetz-Endung → lokales Zertifikat zu erwarten."""
    h = (host or "").strip().lower().rstrip(".")
    if h.startswith("[") and "]" in h:
        h = h[1:h.index("]")]
    elif h.count(":") == 1:
        h = h.split(":", 1)[0]
    try:
        ipaddress.ip_address(h)
        return True
    except ValueError:
        pass
    return bool(h) and ("." not in h or h.endswith(LOCAL_SUFFIXES))


def server_pin(host: str | None = None) -> str | None:
    """Pin nur für lokale Adressen. ``host`` = Host-Header der Anfrage."""
    if host is not None and not is_local_host(host):
        return None
    try:
        return spki_pin_from_pem(_cert_path().read_bytes())
    except OSError:
        return None
