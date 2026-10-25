"""Dauerhafte SIP-Anmeldung einer Verbindung in einem eigenen Thread (PLAN-EINSTELLUNGEN Schritt 5).

Hält einen festen UDP-Port, meldet sich an, erneuert bei der Hälfte der gewährten Zeit und meldet beim Stoppen ab
(Expires 0). Anfragen der Anlage werden beantwortet: OPTIONS → 200, INVITE → 480 (Etappe 1 nimmt noch keine Anrufe an;
andere Telefone klingeln weiter), BYE/CANCEL → 200 bzw. 481. Anfragen anderer Absender werden verworfen.
Bei falschem Kennwort wird nicht erneut versucht (die FRITZ!Box sperrt sonst die Nebenstelle).
"""
from __future__ import annotations

import logging
import os
import socket
import threading
import time
from collections.abc import Callable

from . import message
from .dispatch import CallDispatcher
from .register import RegState, register

logger = logging.getLogger(__name__)
_STOP_STATES = {"auth_failed", "not_found", "port_in_use"}


def source_ip_for(target: tuple[str, int]) -> str:
    """Eigene Adresse auf dem Weg zur Anlage (Routing des Systems; es wird nichts gesendet).

    Wichtig bei mehreren Netzen, z. B. Kabel ins Heimnetz und WLAN zur FRITZ!Box: Die Anlage muss in Via/Contact
    die Adresse sehen, über die sie uns erreicht – nie 0.0.0.0.
    """
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(target)
        return probe.getsockname()[0]
    finally:
        probe.close()


class SipAgent:
    def __init__(self, *, connection_id: str, user: str, password: str, domain: str, target: tuple[str, int],
                 bind: tuple[str, int], display_name: str, interval: int,
                 on_status: Callable[[str], None] | None = None, register_timeout: float = 8.0,
                 retry_delays: tuple[float, ...] = (15, 30, 60, 120, 300),
                 call_policy: Callable[[], str | None] | None = None, call_record: Callable[[dict], None] | None = None,
                 rtp_ports: tuple[int, int] = (7078, 7109), call_options: dict | None = None,
                 call_assistant: Callable[[], dict | None] | None = None) -> None:
        self.connection_id = connection_id
        self._state = RegState(user=user, password=password, domain=domain, target=target, local=bind,
                               display_name=display_name)
        self._bind, self._interval = bind, interval
        self._on_status = on_status
        self._timeout, self._retry = register_timeout, retry_delays
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._sock: socket.socket | None = None
        self.status = "disconnected"
        self.local_addr: tuple[str, int] | None = None
        self.ignored = 0
        self.calls = CallDispatcher(policy=call_policy or (lambda: None), rtp_ports=rtp_ports,
                                    record=call_record or (lambda r: None), **(call_options or {}))
        if call_assistant is not None:
            self.calls.assistant = call_assistant

    def __repr__(self) -> str:
        return f"SipAgent({self.connection_id!r}, status={self.status!r})"

    @property
    def alive(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def _set(self, code: str) -> None:
        self.status = code
        if self._on_status:
            try:
                self._on_status(code)
            except Exception:
                logger.warning("telephony: Statusmeldung fehlgeschlagen", exc_info=True)

    def start(self) -> None:
        if self.alive:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name=f"tel-sip-{self.connection_id}", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 4.0) -> None:
        self._stop.set()
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout)

    def _run(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.bind(self._bind)
        except OSError:
            sock.close()
            self._set("port_in_use")
            return
        self._sock = sock
        self.local_addr = sock.getsockname()
        host = self.local_addr[0]
        if host in ("0.0.0.0", ""):
            try:
                host = source_ip_for(self._state.target)
            except OSError:
                sock.close()
                self._set("unreachable")
                return
        self._state.local = (host, self.local_addr[1])
        try:
            self._loop(sock)
        finally:
            self.calls.hangup_all()
            if self.status == "registered":
                try:
                    register(sock, self._state, 0, timeout=2.0, on_request=self._handle)
                except OSError:
                    pass
            sock.close()
            self._sock = None
            if self.status not in _STOP_STATES:
                self._set("disconnected")

    def _loop(self, sock: socket.socket) -> None:
        failures = 0
        self._set("connecting")
        while not self._stop.is_set():
            try:
                result = register(sock, self._state, self._interval, timeout=self._timeout, on_request=self._handle)
            except OSError:
                result = None
            if self._stop.is_set():
                return
            if result is not None and result.code == "registered":
                failures = 0
                self._set("registered")
                self._serve(sock, max(1.0, result.expires / 2))
                continue
            code = result.code if result is not None else "unreachable"
            self._set(code)
            if code in _STOP_STATES:
                self._serve(sock, None)                # angemeldet bleiben geht nicht; nur noch Anfragen beantworten
                return
            delay = self._retry[min(failures, len(self._retry) - 1)]
            failures += 1
            self._serve(sock, delay)

    def _serve(self, sock: socket.socket, seconds: float | None) -> None:
        """Bis zum nächsten Anmelden bzw. Stop: Anfragen der Anlage beantworten."""
        end = None if seconds is None else time.monotonic() + seconds
        while not self._stop.is_set():
            left = 0.25 if end is None else min(0.25, end - time.monotonic())
            if left <= 0:
                return
            sock.settimeout(left)
            try:
                data, addr = sock.recvfrom(65535)
            except TimeoutError:
                continue
            except OSError:
                return
            try:
                msg = message.parse(data)
            except message.ParseError:
                continue
            if msg.is_request:
                self._handle(msg, addr)
            elif addr == self._state.target:
                self.calls.handle_response(msg)                 # z. B. 200 auf unser BYE

    def _handle(self, msg: message.Message, addr: tuple[str, int]) -> None:
        if addr != self._state.target or self._sock is None:
            self.ignored += 1                               # nur die eigene Anlage (IP und SIP-Port)
            return
        if self.calls.handle_request(self._sock, msg, addr, self._state.local[0]):
            return                                          # INVITE/ACK/BYE/CANCEL: Anrufannahme (sip/dispatch.py)
        code, reason = {"OPTIONS": (200, "OK")}.get(msg.method, (405, "Method Not Allowed"))
        extra = [("Allow", "INVITE, ACK, CANCEL, BYE, OPTIONS")] if code in (200, 405) else []
        try:
            self._sock.sendto(message.build_response(msg, code, reason, to_tag=os.urandom(4).hex(), extra=extra),
                              addr)
        except (OSError, ValueError):
            pass
