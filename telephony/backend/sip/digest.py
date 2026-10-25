"""Digest-Anmeldung für SIP (RFC 2617, RFC 8760: MD5 und SHA-256, qop leer oder „auth“).

Nicht unterstützt (→ Unsupported): andere Verfahren, ``-sess``, ``auth-int`` und Werte mit Anführungszeichen oder
Zeilenumbrüchen (würden sonst in unsere Kopfzeile wandern).
"""
from __future__ import annotations

import hashlib
import os
import re

_PARAM_RE = re.compile(r'([A-Za-z0-9_-]+)\s*=\s*(?:"((?:[^"\\]|\\.)*)"|([^\s,]+))')
_HASH = {"MD5": hashlib.md5, "SHA-256": hashlib.sha256}


class Unsupported(ValueError):
    pass


def parse_challenge(value: str) -> dict[str, str]:
    scheme, _, rest = (value or "").strip().partition(" ")
    params = {"_scheme": scheme.lower()}
    for m in _PARAM_RE.finditer(rest):
        params[m.group(1).lower()] = m.group(2) if m.group(2) is not None else m.group(3)
    return params


def _safe(v: str) -> str:
    if any(ch in v for ch in '"\\\r\n\0'):
        raise Unsupported("unerlaubtes Zeichen in der Anfrage der Gegenstelle")
    return v


def authorization(ch: dict[str, str], method: str, uri: str, user: str, password: str, *,
                  cnonce: str | None = None, nc: int = 1) -> str:
    if ch.get("_scheme") != "digest":
        raise Unsupported("nur Digest")
    realm, nonce = ch.get("realm"), ch.get("nonce")
    if realm is None or not nonce:
        raise Unsupported("realm/nonce fehlt")
    realm, nonce = _safe(realm), _safe(nonce)
    algo = (ch.get("algorithm") or "MD5").upper()
    if algo not in _HASH:
        raise Unsupported(f"Verfahren {algo} nicht unterstützt")
    qops = [q.strip() for q in (ch.get("qop") or "").split(",") if q.strip()]
    if qops and "auth" not in qops:
        raise Unsupported("nur qop=auth")
    h = _HASH[algo]

    def hx(s: str) -> str:
        return h(s.encode()).hexdigest()

    ha1 = hx(f"{user}:{realm}:{password}")
    ha2 = hx(f"{method}:{uri}")
    parts = [f'username="{_safe(user)}"', f'realm="{realm}"', f'nonce="{nonce}"', f'uri="{_safe(uri)}"']
    if qops:
        cnonce = cnonce or os.urandom(8).hex()
        ncs = f"{nc:08x}"
        response = hx(f"{ha1}:{nonce}:{ncs}:{cnonce}:auth:{ha2}")
        parts += [f'response="{response}"', "qop=auth", f"nc={ncs}", f'cnonce="{cnonce}"']
    else:
        parts.append(f'response="{hx(f"{ha1}:{nonce}:{ha2}")}"')
    parts.append(f"algorithm={algo}")
    if ch.get("opaque") is not None:
        parts.append(f'opaque="{_safe(ch["opaque"])}"')
    return "Digest " + ", ".join(parts)
