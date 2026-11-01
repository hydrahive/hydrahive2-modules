"""Zertifikat der Dream Machine fest annehmen (Pinning).

Die Dream Machine hat ein selbst ausgestelltes Zertifikat (CN=unifi.local, ohne CA-Merkmal). Python lehnt es
auch als „vertrauenswürdige CA“ ab (gemessen 01.11.: „invalid CA certificate“). Deshalb: TLS ohne CA-Prüfung,
aber direkt nach dem Handshake – BEVOR Kopfzeilen mit dem Schlüssel gesendet werden – wird der SHA-256 des
Zertifikats mit dem bestätigten Wert verglichen (httpx-Trace „connection.start_tls.complete“). Gemessen: bei
falschem Wert werden keine Kopfzeilen gesendet.
"""
from __future__ import annotations

import asyncio
import hashlib
import ssl


class PinMismatch(Exception):
    def __init__(self, got: str):
        super().__init__(got[:16])
        self.got = got


def fingerprint(der: bytes) -> str:
    return hashlib.sha256(der).hexdigest()


def pretty(fp: str) -> str:
    up = fp.upper()
    return ":".join(up[i:i + 2] for i in range(0, len(up), 2))


def no_ca_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def make_trace(pin: str):
    async def trace(name: str, info: dict) -> None:
        if name != "connection.start_tls.complete":
            return
        stream = info.get("return_value")
        sslobj = stream.get_extra_info("ssl_object") if stream is not None else None
        der = sslobj.getpeercert(binary_form=True) if sslobj is not None else None
        got = fingerprint(der) if der else ""
        if got != pin:
            raise PinMismatch(got)
    return trace


async def fetch_fingerprint(host: str, port: int) -> str:
    """Fingerabdruck holen, ohne etwas zu senden (zum Bestätigen in der Oberfläche)."""
    _reader, writer = await asyncio.wait_for(
        asyncio.open_connection(host, port, ssl=no_ca_context(), server_hostname=None), timeout=8)
    try:
        der = writer.get_extra_info("ssl_object").getpeercert(binary_form=True)
    finally:
        writer.close()
    return fingerprint(der)
