"""Bekannte Anbieter → IMAP/SMTP-Einstellungen (Konto-Assistent, Spec §6). Unbekannt: imap./smtp.<domain> raten."""
from __future__ import annotations

import re

_ADDR = re.compile(r"^[A-Za-z0-9._%+'-]{1,64}@((?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63})$")
_GMAIL_HINT = ("Gmail: Bitte ein App-Passwort verwenden (Google-Konto → Sicherheit → 2-Schritt-Bestätigung → "
               "App-Passwörter). Das normale Google-Passwort funktioniert für IMAP nicht.")

_MS = {"imap_host": "outlook.office365.com", "smtp_host": "smtp-mail.outlook.com", "smtp_port": 587,
       "smtp_tls": "starttls", "auth": "oauth_microsoft", "hint": "Microsoft-Konten melden sich ohne Passwort an: „Mit Microsoft anmelden“."}

_KNOWN: dict[str, dict] = {
    "gmail.com": {"imap_host": "imap.gmail.com", "smtp_host": "smtp.gmail.com", "hint": _GMAIL_HINT},
    "googlemail.com": {"imap_host": "imap.gmail.com", "smtp_host": "smtp.gmail.com", "hint": _GMAIL_HINT},
    "gmx.de": {"imap_host": "imap.gmx.net", "smtp_host": "mail.gmx.net", "smtp_port": 587, "smtp_tls": "starttls",
               "hint": "GMX: IMAP-Zugriff in den GMX-Einstellungen (POP3/IMAP Abruf) einschalten."},
    "gmx.net": {"imap_host": "imap.gmx.net", "smtp_host": "mail.gmx.net", "smtp_port": 587, "smtp_tls": "starttls",
                "hint": "GMX: IMAP-Zugriff in den GMX-Einstellungen (POP3/IMAP Abruf) einschalten."},
    "web.de": {"imap_host": "imap.web.de", "smtp_host": "smtp.web.de", "smtp_port": 587, "smtp_tls": "starttls",
               "hint": "WEB.DE: IMAP-Zugriff in den Einstellungen (POP3/IMAP Abruf) einschalten."},
    "posteo.de": {"imap_host": "posteo.de", "smtp_host": "posteo.de", "smtp_port": 465},
    "mailbox.org": {"imap_host": "imap.mailbox.org", "smtp_host": "smtp.mailbox.org", "smtp_port": 465},
    "t-online.de": {"imap_host": "secureimap.t-online.de", "smtp_host": "securesmtp.t-online.de", "smtp_port": 465,
                    "hint": "Telekom: eigenes E-Mail-Passwort im Kundencenter anlegen."},
    "outlook.com": _MS,
    "hotmail.com": _MS,
}
for _alias in ("outlook.de", "outlook.at", "outlook.fr", "hotmail.de", "hotmail.co.uk", "hotmail.fr", "live.com",
               "live.de", "live.at", "msn.com"):
    _KNOWN[_alias] = _MS
for _alias in ("ionos.de", "online.de"):
    _KNOWN[_alias] = {"imap_host": "imap.ionos.de", "smtp_host": "smtp.ionos.de", "smtp_port": 465}
_KNOWN["strato.de"] = {"imap_host": "imap.strato.de", "smtp_host": "smtp.strato.de", "smtp_port": 465}


def domain(address: str) -> str:
    if not isinstance(address, str) or len(address) > 254:
        raise ValueError("ungültige Mailadresse")
    m = _ADDR.match(address.strip())
    if not m:
        raise ValueError("ungültige Mailadresse")
    return m.group(1).lower()


def suggest(address: str) -> dict:
    d = domain(address)
    base = {"imap_port": 993, "imap_tls": "ssl", "smtp_port": 465, "smtp_tls": "ssl", "hint": "", "auth": "password"}
    known = _KNOWN.get(d)
    if known:
        return {**base, **known, "known": True}
    return {**base, "imap_host": f"imap.{d}", "smtp_host": f"smtp.{d}", "known": False}
