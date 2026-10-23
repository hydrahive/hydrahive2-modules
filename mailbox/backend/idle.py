"""IMAP IDLE auf dem Posteingang (PLAN-M2 Schritt 9, RFC 2177) – neue Mails in Sekunden statt alle 5 Minuten.

Je Konto ein Thread. Ablauf: anmelden → Posteingang nur lesend (EXAMINE) → IDLE; meldet der Server EXISTS/EXPUNGE,
wird ein Abgleich angestoßen (entprellt). Spätestens nach max_idle (25 min < 29 min aus RFC 2177) DONE und neu.
Ohne IDLE beim Server: aufgeben – der 5-Minuten-Takt des Abgleich-Jobs bleibt. Abbruch → neu verbinden mit
wachsender Wartezeit; Anmeldung abgelehnt → lange warten (sonst sperrt der Anbieter das Konto).

Python 3.12 und 3.14: IMAP4.idle() gibt es erst ab 3.14, und die Lesepuffer unterscheiden sich. Genutzt werden nur
_new_tag, send, readline, socket. Kein Socket-Timeout (macht unter 3.12 die Datei-Hülle dauerhaft unbrauchbar),
stattdessen select() + Blick in den Puffer.
"""
from __future__ import annotations

import imaplib
import logging
import re
import select
import threading
import time

from . import auth_login

log = logging.getLogger("hydrahive.modules.mailbox")
_EVENT = re.compile(rb"^\* \d+ (EXISTS|EXPUNGE)\b", re.IGNORECASE)


class Unsupported(RuntimeError):
    pass


def _caps(conn) -> set[str]:
    typ, data = conn.capability()
    return set((data[0] or b"").decode(errors="replace").upper().split()) if typ == "OK" and data else set()


def _buffered(conn) -> bool:
    """Liegt schon eine ganze Zeile im Lesepuffer von imaplib? select() sieht diese Daten nicht.
    3.14: eigene Liste conn._readbuf. 3.12: gepufferte Datei conn.file – peek() bei kurz nicht-blockierendem Socket
    liefert nur, was schon da ist, und blockiert nie (geprüft unter 3.12 und 3.14)."""
    buf = getattr(conn, "_readbuf", None)
    if buf is not None:
        return any(b"\n" in part for part in buf)
    f = getattr(conn, "file", None)
    if f is None:
        return False
    sock = conn.socket()
    timeout = sock.gettimeout()
    sock.setblocking(False)
    try:
        return b"\n" in f.peek(0)
    except (BlockingIOError, OSError, ValueError):
        return False
    finally:
        sock.settimeout(timeout)


def _readline(conn, timeout: float) -> bytes | None:
    """Eine Zeile oder None bei Zeitablauf. Leere Antwort = Verbindung weg."""
    if not _buffered(conn):
        ready, _, _ = select.select([conn.socket()], [], [], timeout)
        if not ready:
            return None
    line = conn.readline()
    if not line:
        raise ConnectionError("Verbindung geschlossen")
    return line


def _idle_round(conn, stop: threading.Event, on_event, *, poll: float, max_idle: float, start_timeout: float,
                tick=lambda: None) -> None:
    tag = conn._new_tag()
    conn.send(tag + b" IDLE\r\n")
    line = _readline(conn, start_timeout)
    while line is not None and line.startswith(b"* "):        # Meldungen vor der Fortsetzung
        if _EVENT.match(line):
            on_event()
        line = _readline(conn, start_timeout)
    if line is None or not line.startswith(b"+"):
        raise Unsupported(f"IDLE abgelehnt: {(line or b'')[:80]!r}")
    end = time.monotonic() + max_idle
    while not stop.is_set() and time.monotonic() < end:
        line = _readline(conn, poll)
        if line is not None and _EVENT.match(line):
            on_event()
        tick()                              # zurückgehaltenen Abgleich nachholen, sobald das Fenster vorbei ist
    conn.send(b"DONE\r\n")
    while (line := _readline(conn, start_timeout)) is not None:       # bis zur Abschlusszeile
        if line.startswith(tag):
            return
        if _EVENT.match(line):
            on_event()
    raise ConnectionError("keine Antwort auf DONE")


class _Debounce:
    """Höchstens ein Abgleich je Fenster; was im Fenster kommt, wird danach nachgeholt (nichts geht verloren)."""

    def __init__(self, fn, window: float):
        self.fn, self.window, self.last, self.pending = fn, window, 0.0, False

    def hit(self) -> None:
        self.pending = True
        self.flush()

    def flush(self) -> None:
        if self.pending and time.monotonic() - self.last >= self.window:
            self.pending, self.last = False, time.monotonic()
            try:
                self.fn()
            except Exception as e:  # noqa: BLE001 - ein kaputter Abgleich darf IDLE nicht beenden
                log.warning("Mailbox-IDLE: Abgleich fehlgeschlagen: %s", str(e)[:200])


def watch(acc: dict, stop: threading.Event, trigger, *, open_conn, password_of, poll: float = 5.0,
          max_idle: float = 25 * 60, backoff: tuple = (5, 15, 60, 300), auth_backoff: float = 3600,
          debounce: float = 10.0, start_timeout: float = 30.0) -> str:
    """Läuft bis stop gesetzt ist. Rückgabe: "stopped" | "unsupported"."""
    deb = _Debounce(lambda: trigger(acc), debounce)
    failures = 0
    while not stop.is_set():
        conn = None
        try:
            conn = open_conn(acc)
            if "IDLE" not in _caps(conn):
                return "unsupported"
            try:
                auth_login.imap_login(conn, acc, password_of(acc["id"]))
            except imaplib.IMAP4.error:
                if stop.wait(auth_backoff):
                    break
                continue
            typ, _ = conn.select("INBOX", readonly=True)
            if typ != "OK":
                raise ConnectionError("Posteingang nicht lesbar")
            failures = 0
            while not stop.is_set():
                _idle_round(conn, stop, deb.hit, poll=poll, max_idle=max_idle, start_timeout=start_timeout,
                            tick=deb.flush)
        except Unsupported:
            return "unsupported"
        except (OSError, imaplib.IMAP4.abort, imaplib.IMAP4.error, ConnectionError) as e:
            wait = backoff[min(failures, len(backoff) - 1)]
            failures += 1
            log.info("Mailbox-IDLE %s: %s – neuer Versuch in %ss", acc.get("id"), str(e)[:120], wait)
            if stop.wait(wait):
                break
        finally:
            if conn is not None:
                try:
                    conn.logout()
                except Exception:  # noqa: BLE001
                    pass
    return "stopped"
