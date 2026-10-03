"""HTTPS zum HydraHive-Server — nur Standardbibliothek.

Vertrauen: Mit ``pin`` (sha256//<base64> über den öffentlichen Schlüssel,
curl-Format) vertraut der Rig genau diesem Server-Schlüssel, auch bei selbst
ausgestellten Zertifikaten. Ohne Pin: normale Prüfung gegen die System-CAs.
Die Prüfung wird nie einfach abgeschaltet.
"""
from __future__ import annotations

import base64
import hashlib
import http.client
import json
import ssl
from urllib.parse import urlsplit

TIMEOUT = 20
DEVICE_BASE = "/api/module-device/mining"


class ClientError(RuntimeError):
    def __init__(self, status: int, detail: str) -> None:
        super().__init__(f"{status}: {detail}")
        self.status = status


def _spki_pin(der_cert: bytes) -> str:
    """Pin aus dem DER-Zertifikat — ohne cryptography (SPKI per ASN.1-Durchlauf)."""
    return "sha256//" + base64.b64encode(hashlib.sha256(extract_spki(der_cert)).digest()).decode()


def _tlv(buf: bytes, pos: int) -> tuple[int, int, int]:
    """(Tag-Start, Inhalts-Start, Ende) eines DER-Elements ab pos."""
    length = buf[pos + 1]
    head = 2
    if length & 0x80:
        n = length & 0x7F
        length = int.from_bytes(buf[pos + 2:pos + 2 + n], "big")
        head = 2 + n
    return pos, pos + head, pos + head + length


def extract_spki(der: bytes) -> bytes:
    """SubjectPublicKeyInfo aus einem X.509-Zertifikat (DER) herausschneiden."""
    _, cert_body, _ = _tlv(der, 0)          # Certificate ::= SEQUENCE
    _, tbs_body, _ = _tlv(der, cert_body)   # tbsCertificate ::= SEQUENCE
    pos = tbs_body
    if der[pos] == 0xA0:                     # [0] version (optional)
        pos = _tlv(der, pos)[2]
    for _ in range(5):                       # serial, signature, issuer, validity, subject
        pos = _tlv(der, pos)[2]
    start, _, end = _tlv(der, pos)           # subjectPublicKeyInfo
    return der[start:end]


class Server:
    def __init__(self, url: str, pin: str | None = None) -> None:
        u = urlsplit(url)
        if u.scheme != "https" or not u.hostname:
            raise ValueError("server_url_must_be_https")
        self.host, self.port, self.pin = u.hostname, u.port or 443, pin

    def _context(self) -> ssl.SSLContext:
        ctx = ssl.create_default_context()
        if self.pin:
            # Vertrauen kommt allein aus dem Pin-Vergleich in _connect().
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        return ctx

    def _connect(self) -> http.client.HTTPSConnection:
        conn = http.client.HTTPSConnection(self.host, self.port, timeout=TIMEOUT, context=self._context())
        conn.connect()
        if self.pin:
            der = conn.sock.getpeercert(binary_form=True)
            if not der or _spki_pin(der) != self.pin:
                conn.close()
                raise ClientError(0, "server_pin_mismatch")
        return conn

    def post(self, path: str, body: dict, headers: dict[str, str]) -> dict:
        conn = self._connect()
        try:
            conn.request("POST", DEVICE_BASE + path, body=json.dumps(body),
                         headers={"Content-Type": "application/json", **headers})
            resp = conn.getresponse()
            raw = resp.read(65536).decode("utf-8", "replace")
        finally:
            conn.close()
        if resp.status >= 300:
            raise ClientError(resp.status, raw[:300])
        return json.loads(raw or "{}")
