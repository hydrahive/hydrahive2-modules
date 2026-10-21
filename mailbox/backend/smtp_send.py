"""Versand über SMTP (PLAN-M2 Schritt 3). Eigene Härtung statt Kern-Transport (der prüft keine Zertifikate):

- verbunden wird mit der vorab geprüften IP (netcheck, kein DNS-Rebinding), das Zertifikat gilt für den Hostnamen
- „ssl“ = SMTPS (465), „starttls“ = 587 mit STARTTLS-Pflicht: bietet der Server es nicht an → Abbruch, kein Klartext
- TLS ≥ 1.2, Zertifikat und Hostname geprüft
- Fehler nach Art (config/blocked/connect/tls/auth/rejected/smtp), Passwort geschwärzt
"""
from __future__ import annotations

import smtplib
import socket
import ssl

from . import netcheck

TIMEOUT = 30


class SendError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    return ctx


class _PinnedSSL(smtplib.SMTP_SSL):
    def __init__(self, host: str, ip: str, port: int, ctx: ssl.SSLContext):
        self._ip = ip
        super().__init__(host=None, context=ctx, timeout=TIMEOUT)
        self._host = host
        self.connect(host, port)

    def _get_socket(self, host, port, timeout):
        sock = socket.create_connection((self._ip, port), timeout)
        return self.context.wrap_socket(sock, server_hostname=host)


class _PinnedPlain(smtplib.SMTP):
    def __init__(self, host: str, ip: str, port: int):
        self._ip = ip
        super().__init__(host=None, timeout=TIMEOUT)
        self._host = host
        self.connect(host, port)

    def _get_socket(self, host, port, timeout):
        return socket.create_connection((self._ip, port), timeout)


def _redact(text: str, password: str) -> str:
    return text.replace(password, "***") if password else text


def _open(acc: dict, allow_internal) -> smtplib.SMTP:
    host, port, tls = (acc.get("smtp_host") or "").strip(), int(acc.get("smtp_port") or 0), acc.get("smtp_tls")
    if not host:
        raise SendError("config", "Kein Postausgangsserver (SMTP) im Konto eingetragen")
    try:
        ip = netcheck.check(host, port, allow_internal=allow_internal)
    except netcheck.HostBlocked as e:
        raise SendError("blocked", f"Postausgangsserver nicht erlaubt: {e}") from None
    ctx = _context()
    if tls == "ssl":
        return _PinnedSSL(host, ip, port, ctx)
    if tls == "starttls":
        conn = _PinnedPlain(host, ip, port)
        try:
            conn.ehlo()
            if not conn.has_extn("starttls"):
                raise SendError("tls", "Server bietet kein STARTTLS an – Versand ohne Verschlüsselung abgelehnt")
            conn.starttls(context=ctx)
            conn.ehlo()
        except BaseException:
            conn.close()
            raise
        return conn
    raise SendError("config", "unbekannte TLS-Art")


def send(acc: dict, password: str, raw: bytes, envelope: list[str], *, allow_internal=frozenset()) -> dict:
    """Mail senden. Gibt {"refused": [...]} zurück, wenn nur einige Empfänger abgelehnt wurden."""
    conn = None
    try:
        conn = _open(acc, allow_internal)
        conn.login(acc.get("username") or acc["address"], password)
        refused = conn.sendmail(acc["address"], envelope, raw)
        return {"refused": sorted(refused)} if refused else {}
    except SendError:
        raise
    except smtplib.SMTPAuthenticationError as e:
        raise SendError("auth", _redact(f"Anmeldung abgelehnt: {e.smtp_code} {e.smtp_error!r}", password)) from None
    except smtplib.SMTPRecipientsRefused as e:
        raise SendError("rejected", "Alle Empfänger abgelehnt: " + ", ".join(sorted(e.recipients))) from None
    except smtplib.SMTPNotSupportedError as e:
        raise SendError("tls", _redact(f"Server unterstützt das nicht: {e}", password)) from None
    except (ssl.SSLError, ssl.CertificateError) as e:
        raise SendError("tls", f"Verschlüsselung/Zertifikat abgelehnt: {e}") from None
    except smtplib.SMTPException as e:
        raise SendError("smtp", _redact(f"Server-Fehler: {e}", password)) from None
    except OSError as e:
        raise SendError("connect", f"Server nicht erreichbar: {e}") from None
    finally:
        if conn is not None:
            try:
                conn.quit()
            except (smtplib.SMTPException, OSError):
                conn.close()
