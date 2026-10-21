"""IMAP-Verbindung (Spec §11): TLS Pflicht, Zertifikat geprüft, verbunden wird mit der geprüften IP (netcheck),
der Hostname dient für SNI und Zertifikatsprüfung. Dazu Ordnerliste mit SPECIAL-USE und UTF-7-Namen.
"""
from __future__ import annotations

import base64
import imaplib
import re
import socket
import ssl

from . import netcheck

TIMEOUT = 60
_LIST = re.compile(rb'^\((?P<flags>[^)]*)\) (?P<delim>"[^"]*"|NIL) (?P<name>.+)$')
_ROLES = {b"\\sent": "sent", b"\\drafts": "drafts", b"\\trash": "trash", b"\\junk": "junk", b"\\archive": "archive",
          b"\\all": "all"}


def utf7_decode(name: str) -> str:
    def dec(m):
        body = m.group(1).replace(",", "/")
        if not body:
            return "&"
        return base64.b64decode(body + "=" * (-len(body) % 4)).decode("utf-16-be")
    return re.sub(r"&([A-Za-z0-9+,]*)-", dec, name)


def utf7_encode(name: str) -> str:
    out, buf = [], []

    def flush():
        if buf:
            b = base64.b64encode("".join(buf).encode("utf-16-be")).rstrip(b"=").replace(b"/", b",").decode()
            out.append("&" + b + "-")
            buf.clear()
    for ch in name:
        if 0x20 <= ord(ch) <= 0x7e:
            flush()
            out.append("&-" if ch == "&" else ch)
        else:
            buf.append(ch)
    flush()
    return "".join(out)


def quote(name: str) -> str:
    enc = utf7_encode(name)
    return '"' + enc.replace("\\", "\\\\").replace('"', '\\"') + '"'


def parse_list(lines: list) -> list[dict]:
    out = []
    for raw in lines:
        if not isinstance(raw, bytes):
            continue
        m = _LIST.match(raw)
        if not m:
            continue
        flags = m.group("flags").lower().split()
        if b"\\noselect" in flags or b"\\nonexistent" in flags:
            continue
        name = m.group("name").strip()
        if name.startswith(b'"') and name.endswith(b'"'):
            name = name[1:-1].replace(b'\\"', b'"').replace(b"\\\\", b"\\")
        text = utf7_decode(name.decode("ascii", errors="replace"))
        delim = m.group("delim").strip(b'"').decode() if m.group("delim") != b"NIL" else ""
        role = "inbox" if text.upper() == "INBOX" else next((_ROLES[f] for f in flags if f in _ROLES), "")
        out.append({"name": text, "role": role, "delim": delim})
    return out


class _PinnedSSL(imaplib.IMAP4_SSL):
    """Verbindet mit der vorab geprüften IP, prüft das Zertifikat aber gegen den Hostnamen."""

    def __init__(self, host: str, ip: str, port: int, ctx: ssl.SSLContext):
        self._ip = ip
        super().__init__(host, port, ssl_context=ctx, timeout=TIMEOUT)

    def _create_socket(self, timeout):
        sock = socket.create_connection((self._ip, self.port), timeout)
        return self.ssl_context.wrap_socket(sock, server_hostname=self.host)


class _PinnedPlain(imaplib.IMAP4):
    def __init__(self, host: str, ip: str, port: int):
        self._ip = ip
        super().__init__(host, port, timeout=TIMEOUT)

    def _create_socket(self, timeout):
        return socket.create_connection((self._ip, self.port), timeout)


def open_connection(account: dict, *, allow_internal: set[str] = frozenset()):
    """Verbindung aufbauen (ohne Login). ssl = IMAPS 993; starttls = 143 mit Pflicht-STARTTLS."""
    host, port, tls = account["imap_host"], int(account["imap_port"]), account["imap_tls"]
    ip = netcheck.check(host, port, allow_internal=allow_internal)
    ctx = ssl.create_default_context()
    if tls == "ssl":
        return _PinnedSSL(host, ip, port, ctx)
    if tls == "starttls":
        conn = _PinnedPlain(host, ip, port)
        conn.starttls(ssl_context=ctx)
        return conn
    raise ValueError("unbekannte TLS-Art")
