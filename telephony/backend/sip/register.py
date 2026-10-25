"""Ein SIP-Anmeldevorgang über einen vorhandenen UDP-Socket (RFC 3261 §10, §17.1.2, RFC 3581).

Ablauf: REGISTER → 401/407 mit Digest-Challenge → REGISTER mit Anmeldung → 200 (oder Fehler). Wiederholung ohne Antwort
nach T1 = 0,5 s, verdoppelnd. Nur Antworten von der Anlagenadresse mit passender Call-ID/CSeq zählen. Lernt die Anlage
uns unter einer anderen Adresse (Via received/rport, Router dazwischen), wird diese als Contact angemeldet – sonst
kämen Anrufe nie an. Fremde Anfragen (OPTIONS, INVITE) während des Wartens gehen an ``on_request``.
"""
from __future__ import annotations

import os
import re
import socket
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from . import digest, message

_T1 = 0.5
_VIA_RE = re.compile(r";received=([0-9.]+)|;rport=(\d+)")


@dataclass
class RegState:
    user: str
    password: str
    domain: str
    target: tuple[str, int]
    local: tuple[str, int]
    display_name: str = "HydraHive"
    call_id: str = field(default_factory=lambda: os.urandom(12).hex() + "@hydrahive")
    tag: str = field(default_factory=lambda: os.urandom(6).hex())
    cseq: int = 0
    contact: tuple[str, int] | None = None


@dataclass
class RegResult:
    code: str
    expires: int = 0
    status: int = 0


def _branch() -> str:
    return "z9hG4bK" + os.urandom(8).hex()


def _request(st: RegState, expires: int, contact: tuple[str, int],
             auth: tuple[str, str] | None) -> tuple[bytes, int]:
    st.cseq += 1
    headers = [
        ("Via", f"SIP/2.0/UDP {st.local[0]}:{st.local[1]};rport;branch={_branch()}"),
        ("Max-Forwards", "70"),
        ("From", f'"{st.display_name}" <sip:{st.user}@{st.domain}>;tag={st.tag}'),
        ("To", f"<sip:{st.user}@{st.domain}>"),
        ("Call-ID", st.call_id),
        ("CSeq", f"{st.cseq} REGISTER"),
        ("Contact", f"<sip:{st.user}@{contact[0]}:{contact[1]}>"),
        ("Expires", str(expires)),
        ("Allow", "INVITE, ACK, CANCEL, BYE, OPTIONS"),
        ("User-Agent", "HydraHive"),
    ]
    if auth:
        headers.append(auth)
    return message.build_request("REGISTER", f"sip:{st.domain}", headers), st.cseq


def _learned(resp: message.Message) -> tuple[str, int] | None:
    via = resp.header("via") or ""
    host = port = None
    for m in _VIA_RE.finditer(via):
        host = m.group(1) or host
        port = int(m.group(2)) if m.group(2) else port
    return (host, port) if host and port else None


def _granted(resp: message.Message, asked: int) -> int:
    for c in resp.headers_all("contact"):
        m = re.search(r";\s*expires=(\d+)", c)
        if m:
            return int(m.group(1))
    v = resp.header("expires")
    return int(v) if v and v.isdigit() else asked


def _exchange(sock: socket.socket, st: RegState, raw: bytes, cseq: int, deadline: float,
              on_request: Callable | None) -> message.Message | None:
    interval, next_send = _T1, 0.0
    while True:
        now = time.monotonic()
        if now >= deadline:
            return None
        if now >= next_send:
            sock.sendto(raw, st.target)
            next_send, interval = now + interval, min(interval * 2, 4.0)
        sock.settimeout(max(0.01, min(next_send, deadline) - time.monotonic()))
        try:
            data, addr = sock.recvfrom(65535)
        except TimeoutError:
            continue
        if addr != st.target:
            continue                                         # nur die Anlage selbst (IP und SIP-Port)
        try:
            msg = message.parse(data)
        except message.ParseError:
            continue
        if msg.is_request:
            if on_request:
                on_request(msg, addr)
            continue
        if msg.header("call-id") != st.call_id or msg.header("cseq") != f"{cseq} REGISTER":
            continue
        if 100 <= msg.status < 200:
            continue
        return msg


def _once(sock: socket.socket, st: RegState, expires: int, contact: tuple[str, int], deadline: float,
          on_request: Callable | None) -> tuple[RegResult, message.Message | None]:
    """Eine Anmeldung für genau einen Contact inkl. Digest-Runde und 423 (Mindest-Ablaufzeit)."""
    auth: tuple[str, str] | None = None
    tried_auth = interval_fixed = False
    while True:
        raw, cseq = _request(st, expires, contact, auth)
        resp = _exchange(sock, st, raw, cseq, deadline, on_request)
        if resp is None:
            return RegResult("unreachable"), None
        if resp.status in (401, 407):
            if tried_auth:
                return RegResult("auth_failed", status=resp.status), resp
            proxy = resp.status == 407
            hdr = resp.header("proxy-authenticate" if proxy else "www-authenticate")
            try:
                value = digest.authorization(digest.parse_challenge(hdr or ""), "REGISTER", f"sip:{st.domain}",
                                             st.user, st.password)
            except digest.Unsupported:
                return RegResult("rejected", status=resp.status), resp
            auth, tried_auth = ("Proxy-Authorization" if proxy else "Authorization", value), True
            continue
        if resp.status == 423 and not interval_fixed:
            m = resp.header("min-expires")
            if m and m.isdigit() and 0 < int(m) <= 7200:
                expires, interval_fixed, tried_auth, auth = int(m), True, False, None
                continue
        if resp.status == 200:
            return RegResult("registered", expires=_granted(resp, expires) if expires else 0, status=200), resp
        if resp.status == 403:
            return RegResult("auth_failed", status=403), resp
        if resp.status == 404:
            return RegResult("not_found", status=404), resp
        return RegResult("rejected", status=resp.status), resp


def register(sock: socket.socket, st: RegState, expires: int, *, timeout: float = 8.0,
             on_request: Callable | None = None) -> RegResult:
    deadline = time.monotonic() + timeout
    contact = st.contact or st.local
    result, resp = _once(sock, st, expires, contact, deadline, on_request)
    learned = _learned(resp) if resp is not None and result.code == "registered" else None
    if expires and learned and learned != contact:
        # Router dazwischen: Die Anlage sieht uns unter `learned`. Alte Adresse abmelden, die gelernte anmelden.
        _once(sock, st, 0, contact, deadline, on_request)
        st.contact = learned
        result, _ = _once(sock, st, expires, learned, deadline, on_request)
    return result
