"""Fingerabdruck des Server-Zertifikats für den Kopplungsbefehl.

HydraHive-Installationen nutzen meist ein selbst ausgestelltes Zertifikat
(installer/modules/60-nginx.sh → <config_dir>/tls/hydrahive.crt). Der Rig
vertraut genau diesem Zertifikat (Pinning), statt die Prüfung abzuschalten.
Fehlt die Datei (z. B. Proxy mit echtem Zertifikat), gibt es keinen Pin —
dann prüft der Rig ganz normal gegen die System-CAs.
"""
from __future__ import annotations

import base64
import hashlib
import logging
from pathlib import Path

from hydrahive.settings import settings

logger = logging.getLogger(__name__)


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
        logger.warning("Mining: Server-Zertifikat nicht lesbar: %s", exc)
        return None
    return "sha256//" + base64.b64encode(hashlib.sha256(spki).digest()).decode("ascii")


def server_pin() -> str | None:
    try:
        return spki_pin_from_pem(_cert_path().read_bytes())
    except OSError:
        return None
