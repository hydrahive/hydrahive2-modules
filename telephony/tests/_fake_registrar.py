"""Echter UDP-Registrar für Tests: verhält sich wie eine FRITZ!Box (401-Challenge, Digest-Prüfung, 200/403).

Prüft den Digest wirklich mit dem bekannten Kennwort. Zeichnet alle Anfragen auf. Optional: „NAT“ (meldet in Via
received/rport eine andere Adresse), stumm (keine Antwort), feste Antwort-Codes, Mindest-Ablaufzeit.
"""
from __future__ import annotations

import hashlib
import re
import socket
import threading

from backend.sip import message


class FakeRegistrar:
    def __init__(self, user: str = "hydra-telefon", password: str = "Sehr-Geheim-42", realm: str = "fritz.box",
                 *, nat: tuple[str, int] | None = None, silent: bool = False, fixed: int | None = None,
                 min_expires: int | None = None, max_expires: int | None = None,
                 rechallenge: bool = False) -> None:
        self.user, self.password, self.realm = user, password, realm
        self.nat, self.silent, self.fixed = nat, silent, fixed
        self.min_expires, self.max_expires = min_expires, max_expires
        self.rechallenge = rechallenge
        self.requests: list[message.Message] = []
        self.sources: list[tuple[str, int]] = []
        self.bindings: dict[str, int] = {}          # Contact → Ablauf in s (0 = abgemeldet)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 0))
        self.port = self.sock.getsockname()[1]
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def close(self) -> None:
        self._stop.set()
        self.sock.close()

    def send(self, raw: bytes, addr: tuple[str, int]) -> None:
        self.sock.sendto(raw, addr)

    def _loop(self) -> None:
        self.sock.settimeout(0.05)
        while not self._stop.is_set():
            try:
                raw, addr = self.sock.recvfrom(65535)
            except TimeoutError:
                continue
            except OSError:
                return
            try:
                msg = message.parse(raw)
            except message.ParseError:
                continue
            self.requests.append(msg)
            self.sources.append(addr)
            if msg.is_request and msg.method == "REGISTER" and not self.silent:
                self.sock.sendto(self._answer(msg, addr), addr)
            elif msg.is_request and msg.method == "BYE" and not self.silent:
                self.sock.sendto(message.build_response(msg, 200, "OK"), addr)

    def _via_ext(self, msg: message.Message, addr) -> message.Message:
        host, port = self.nat or addr
        via = msg.header("via") or ""
        via = re.sub(r";rport(?=;|$)", f";rport={port}", via) + f";received={host}"
        msg.headers = [("via", via) if k == "via" else (k, v) for k, v in msg.headers]
        return msg

    def _answer(self, msg: message.Message, addr) -> bytes:
        msg = self._via_ext(msg, addr)
        if self.fixed:
            return message.build_response(msg, self.fixed, "Fixed", to_tag="srv")
        auth = msg.header("authorization")
        if not auth or self.rechallenge:
            return message.build_response(msg, 401, "Unauthorized", to_tag="srv", extra=[
                ("WWW-Authenticate", f'Digest realm="{self.realm}", nonce="N{len(self.requests)}", algorithm=MD5')])
        if not self._digest_ok(auth, msg):
            return message.build_response(msg, 403, "Forbidden", to_tag="srv")
        expires = int(msg.header("expires") or "3600")
        if self.min_expires and 0 < expires < self.min_expires:
            return message.build_response(msg, 423, "Interval Too Brief", to_tag="srv",
                                          extra=[("Min-Expires", str(self.min_expires))])
        if self.max_expires and expires > self.max_expires:
            expires = self.max_expires
        contact = (msg.header("contact") or "").split(";")[0]
        self.bindings[contact] = expires
        return message.build_response(msg, 200, "OK", to_tag="srv",
                                      extra=[("Contact", f"{contact};expires={expires}")])

    def _digest_ok(self, auth: str, msg: message.Message) -> bool:
        p = dict(re.findall(r'(\w+)="?([^",]+)"?', auth))
        if p.get("username") != self.user:
            return False
        ha1 = hashlib.md5(f"{self.user}:{self.realm}:{self.password}".encode()).hexdigest()
        ha2 = hashlib.md5(f"REGISTER:{p.get('uri')}".encode()).hexdigest()
        return p.get("response") == hashlib.md5(f"{ha1}:{p.get('nonce')}:{ha2}".encode()).hexdigest()

    def registers(self) -> list[message.Message]:
        return [m for m in self.requests if m.is_request and m.method == "REGISTER"]
