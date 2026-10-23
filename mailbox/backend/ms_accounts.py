"""Microsoft-Konten anlegen und neu anmelden (PLAN-M1b). Server sind fest (Microsoft), kein Passwort.

Ablauf: Anmelde-Vorgang fertig (ms_flows) → Tokens genau einmal abholen → IMAP-Anmeldung prüfen → speichern.
Schlägt die Prüfung fehl, wird nichts gespeichert (wie bei Passwort-Konten).
"""
from __future__ import annotations

import secrets as _rand

from hydrahive.db._utils import now_iso
from hydrahive.db.connection import db

from . import accounts, ms_flows, ms_tokens, providers

IMAP = {"imap_host": "outlook.office365.com", "imap_port": 993, "imap_tls": "ssl"}
SMTP_PRIVATE = {"smtp_host": "smtp-mail.outlook.com", "smtp_port": 587, "smtp_tls": "starttls"}
SMTP_365 = {"smtp_host": "smtp.office365.com", "smtp_port": 587, "smtp_tls": "starttls"}
FIXED = frozenset({"imap_host", "imap_port", "imap_tls", "smtp_host", "smtp_port", "smtp_tls", "username", "password"})


def servers(address: str) -> dict:
    """Private Adressen (outlook.de, hotmail …) senden über smtp-mail.outlook.com, Microsoft 365 über
    smtp.office365.com."""
    private = providers.suggest(address).get("auth") == "oauth_microsoft"
    return {**IMAP, **(SMTP_PRIVATE if private else SMTP_365)}


def _check(acc: dict, tokens: dict) -> None:
    """IMAP-Anmeldung mit genau diesen Tokens prüfen (vor dem Speichern)."""
    ms_tokens.prime(acc["id"], tokens)
    try:
        accounts._test_login(acc, "")
    except BaseException:
        ms_tokens.forget(acc["id"])
        raise


def create(user: str, flow_id: str, address: str, label: str = "") -> dict:
    providers.domain(address)
    address = address.strip().lower()
    label = (label or "").strip()[:200] or address
    if any(a["address"] == address for a in accounts.list_for(user)):
        raise accounts.Conflict("Konto mit dieser Adresse gibt es schon")
    tokens = ms_flows.take(user, flow_id)
    aid = _rand.token_hex(12)
    acc = {"id": aid, "address": address, "username": address, "auth": "oauth_microsoft", "label": label,
           **servers(address)}
    _check(acc, tokens)
    now = now_iso()
    with db() as c:
        c.execute("INSERT INTO module_mailbox_accounts(id, owner, label, address, sender_name, auth, imap_host, "
                  "imap_port, imap_tls, smtp_host, smtp_port, smtp_tls, username, secret, status, created_at, "
                  "updated_at) "
                  "VALUES (?,?,?,?,'', 'oauth_microsoft', ?,?,?,?,?,?,?,?, 'ok', ?, ?)",
                  (aid, f"user:{user}", label, address, acc["imap_host"], acc["imap_port"], acc["imap_tls"],
                   acc["smtp_host"], acc["smtp_port"], acc["smtp_tls"], address,
                   ms_tokens.seal(aid, tokens["refresh_token"]), now, now))
    ms_tokens.store(aid, tokens)
    return accounts.get_own(user, aid)


def reauth(user: str, aid: str, flow_id: str) -> dict:
    acc = accounts.get_own(user, aid)
    if not acc:
        raise accounts.NotFound(aid)
    if acc["auth"] != "oauth_microsoft":
        raise ValueError("kein Microsoft-Konto")
    tokens = ms_flows.take(user, flow_id)
    _check(acc, tokens)
    ms_tokens.store(aid, tokens)
    accounts.set_status(aid, "ok", "")
    return accounts.get_own(user, aid)
