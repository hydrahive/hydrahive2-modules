"""Echter kleiner IMAP-Server über TCP für die IDLE-Tests (Thread, 127.0.0.1). Spricht genau so viel IMAP, wie
imaplib und backend/idle.py brauchen: CAPABILITY, LOGIN, EXAMINE/SELECT, IDLE/DONE, NOOP, LOGOUT.

Steuerung aus dem Test: push(b"* 5 EXISTS") schickt an alle Sitzungen im IDLE; drop() trennt alle Verbindungen.
"""
from __future__ import annotations

import socket
import threading
import time


class IdleServer:
    def __init__(self, *, idle=True, idle_reply=b"+ idling", password="pw"):
        self.idle, self.idle_reply, self.password = idle, idle_reply, password
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(8)
        self.port = self.sock.getsockname()[1]
        self.logins = 0
        self.idles = 0                     # IDLE-Befehle insgesamt
        self.dones = 0                     # ordentlich beendete IDLE
        self.selects: list[str] = []
        self.conns: list[socket.socket] = []
        self.in_idle: list[socket.socket] = []
        self.lock = threading.Lock()
        threading.Thread(target=self._serve, daemon=True).start()

    def close(self):
        self.sock.close()
        self.drop()

    def drop(self):
        with self.lock:
            for c in self.conns:
                try:
                    c.shutdown(socket.SHUT_RDWR)
                    c.close()
                except OSError:
                    pass
            self.conns.clear()
            self.in_idle.clear()

    def push(self, line: bytes):
        with self.lock:
            for c in list(self.in_idle):
                try:
                    c.sendall(line + b"\r\n")
                except OSError:
                    pass

    def wait_idle(self, n=1, timeout=5.0) -> bool:
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            with self.lock:
                if len(self.in_idle) >= n:
                    return True
            time.sleep(0.02)
        return False

    def _serve(self):
        while True:
            try:
                c, _ = self.sock.accept()
            except OSError:
                return
            with self.lock:
                self.conns.append(c)
            threading.Thread(target=self._session, args=(c,), daemon=True).start()

    def _session(self, c):
        f = c.makefile("rb")
        send = c.sendall
        try:
            send(b"* OK test ready\r\n")
            idle_tag = None
            while line := f.readline():
                parts = line.rstrip(b"\r\n").split(b" ")
                if idle_tag is not None:
                    if parts[0].upper() == b"DONE":
                        with self.lock:
                            self.in_idle.remove(c) if c in self.in_idle else None
                        self.dones += 1
                        send(idle_tag + b" OK IDLE terminated\r\n")
                        idle_tag = None
                    continue
                tag, cmd = parts[0], parts[1].upper() if len(parts) > 1 else b""
                if cmd == b"CAPABILITY":
                    send(b"* CAPABILITY IMAP4rev1" + (b" IDLE" if self.idle else b"") + b"\r\n" + tag + b" OK done\r\n")
                elif cmd == b"LOGIN":
                    self.logins += 1
                    ok = parts[-1].strip(b'"') == self.password.encode()
                    send(tag + (b" OK done\r\n" if ok else b" NO [AUTHENTICATIONFAILED] bad\r\n"))
                elif cmd in (b"SELECT", b"EXAMINE"):
                    self.selects.append(cmd.decode())
                    send(b"* 3 EXISTS\r\n* OK [UIDVALIDITY 1] x\r\n" + tag + b" OK [READ-ONLY] done\r\n")
                elif cmd == b"IDLE":
                    self.idles += 1
                    if not self.idle:
                        send(tag + b" BAD unknown command\r\n")
                        continue
                    send(self.idle_reply + b"\r\n")
                    if self.idle_reply.startswith(b"+"):
                        idle_tag = tag
                        with self.lock:
                            self.in_idle.append(c)
                elif cmd == b"LOGOUT":
                    send(b"* BYE bye\r\n" + tag + b" OK done\r\n")
                    return
                else:
                    send(tag + b" OK done\r\n")
        except OSError:
            pass
        finally:
            with self.lock:
                if c in self.in_idle:
                    self.in_idle.remove(c)
            try:
                c.close()
            except OSError:
                pass
