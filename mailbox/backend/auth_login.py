"""Die eine Stelle, an der Mailbox sich bei IMAP und SMTP anmeldet (PLAN-M1b).

- Passwort-Konten: LOGIN wie bisher
- Microsoft-Konten: SASL XOAUTH2 mit Zugriffstoken (learn.microsoft.com, „Authenticate an IMAP, POP or SMTP connection
  using OAuth“): user=<adresse>^Aauth=Bearer <token>^A^A
- ein Microsoft-Token geht nur an Microsoft-Server (feste Liste) – sonst wird gar kein Token geholt
- Fehler werden in die Ausnahmen übersetzt, die die Aufrufer schon kennen (imaplib.IMAP4.error, SMTP-Ausnahmen,
  OSError bei „Microsoft gerade nicht erreichbar“). Tokens erscheinen nie in Fehlertexten.
Ein Test (test_ms_login) sorgt dafür, dass niemand außerhalb dieser Datei selbst login() aufruft.
"""
from __future__ import annotations

import imaplib
import smtplib

from . import ms_tokens

MICROSOFT = "oauth_microsoft"
MS_IMAP = frozenset({"outlook.office365.com"})
MS_SMTP = frozenset({"smtp-mail.outlook.com", "smtp.office365.com"})


def is_microsoft(acc: dict) -> bool:
    return acc.get("auth") == MICROSOFT


def _user(acc: dict) -> str:
    return acc.get("username") or acc["address"]


def _xoauth(acc: dict, token: str) -> str:
    return f"user={_user(acc)}\x01auth=Bearer {token}\x01\x01"


def _token(acc: dict, host_key: str, allowed: frozenset, err):
    if (acc.get(host_key) or "").strip().lower() not in allowed:
        raise err("Microsoft-Anmeldung nur an Microsoft-Server")
    try:
        return ms_tokens.access_token(acc)
    except ms_tokens.Expired as e:
        raise err(str(e)) from None
    except ms_tokens.Unavailable as e:
        raise ConnectionError(f"Microsoft gerade nicht erreichbar: {e}"[:200]) from None


def imap_login(conn, acc: dict, password: str = "") -> None:
    if not is_microsoft(acc):
        conn.login(_user(acc), password)
        return
    token = _token(acc, "imap_host", MS_IMAP, imaplib.IMAP4.error)
    try:
        conn.authenticate("XOAUTH2", lambda _challenge: _xoauth(acc, token))
    except imaplib.IMAP4.error as e:
        ms_tokens.forget(acc["id"])
        raise imaplib.IMAP4.error(redact(str(e), token)) from None


def smtp_login(conn, acc: dict, password: str = "") -> None:
    if not is_microsoft(acc):
        conn.login(_user(acc), password)
        return
    token = _token(acc, "smtp_host", MS_SMTP, lambda m: smtplib.SMTPAuthenticationError(535, m))
    try:
        # Bei Ablehnung schickt der Server 334 + Fehler-JSON und erwartet eine leere Zeile (RFC 7628 §3.2.3)
        conn.auth("XOAUTH2", lambda challenge=None: _xoauth(acc, token) if challenge is None else "",
                  initial_response_ok=True)
    except smtplib.SMTPAuthenticationError as e:
        ms_tokens.forget(acc["id"])
        raise smtplib.SMTPAuthenticationError(e.smtp_code, redact(str(e.smtp_error), token)) from None


def redact(text: str, secret: str) -> str:
    return text.replace(secret, "***") if secret else text
