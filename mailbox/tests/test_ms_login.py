"""M1b: Zugriffstoken für Microsoft-Konten – Erneuern, Ablauf, neuer Refresh-Token, Widerruf, Netzfehler."""
# ruff: noqa: F811 - pytest-Fixtures aus _ms_base
from __future__ import annotations

import json

import pytest
from _ms_base import CID, _ms_state, app_set, clock, err, ms  # noqa: F401

ADDR = "till@outlook.de"


def _ms_account(rt="RT-1") -> dict:
    """Microsoft-Konto direkt in der DB (wie nach der Anmeldung)."""
    from backend import secrets
    from hydrahive.db._utils import now_iso
    from hydrahive.db.connection import db
    aid, now = "ms" + str(abs(hash(rt)))[:10], now_iso()
    with db() as c:
        c.execute("INSERT INTO module_mailbox_accounts(id, owner, label, address, auth, imap_host, imap_port, "
                  "imap_tls, smtp_host, smtp_port, smtp_tls, username, secret, status, created_at, updated_at) VALUES "
                  "(?, 'user:alice', 'Outlook', ?, 'oauth_microsoft', 'outlook.office365.com', 993, 'ssl', "
                  "'smtp-mail.outlook.com', 587, 'starttls', ?, ?, 'ok', ?, ?)",
                  (aid, ADDR, ADDR, secrets.seal(aid, json.dumps({"refresh_token": rt})), now, now))
    from backend import accounts
    return {**accounts.get_own("alice", aid), "owner": "user:alice"}


def _secret(aid) -> dict:
    from backend import secrets
    from hydrahive.db.connection import db
    with db() as c:
        return json.loads(secrets.open_(aid, c.execute("SELECT secret FROM module_mailbox_accounts WHERE id=?",
                                                       (aid,)).fetchone()[0]))


def test_token_wird_geholt_und_zwischengespeichert(ms, clock, app_set):
    from backend import ms_tokens
    acc = _ms_account()
    assert ms_tokens.access_token(acc) == "AT-1"
    assert ms_tokens.access_token(acc) == "AT-1"
    assert len(ms.calls) == 1, "zweiter Abruf aus dem Speicher"
    assert ms.calls[0][1]["refresh_token"] == "RT-1" and ms.calls[0][1]["client_id"] == CID


def test_kurz_vor_ablauf_wird_erneuert(ms, clock, app_set):
    from backend import ms_tokens
    acc = _ms_account()
    ms_tokens.access_token(acc)
    clock["now"] += 3600 - 299
    ms.token.append((200, {"access_token": "AT-2", "expires_in": 3600}))
    assert ms_tokens.access_token(acc) == "AT-2"
    assert _secret(acc["id"]) == {"refresh_token": "RT-1"}, "ohne neuen Refresh-Token bleibt der alte"


def test_neuer_refresh_token_wird_gespeichert(ms, clock, app_set):
    from backend import ms_tokens
    acc = _ms_account()
    ms.token.append((200, {"access_token": "AT-9", "refresh_token": "RT-NEU", "expires_in": 3600}))
    ms_tokens.access_token(acc)
    assert _secret(acc["id"]) == {"refresh_token": "RT-NEU"}


def test_widerrufen_status_und_kein_dauerfragen(ms, clock, app_set):
    from backend import accounts, ms_tokens
    acc = _ms_account()
    ms.token.append(err("invalid_grant", "AADSTS50173: grant revoked"))
    with pytest.raises(ms_tokens.Expired):
        ms_tokens.access_token(acc)
    a = accounts.get_own("alice", acc["id"])
    assert a["status"] == "auth_failed" and "erneut" in a["status_detail"].lower()
    with pytest.raises(ms_tokens.Expired):
        ms_tokens.access_token(acc)
    assert len(ms.calls) == 1, "nach endgültigem Fehler nicht im Takt weiter bei Microsoft fragen"


def test_netzfehler_ist_nur_vorlaeufig(ms, clock, app_set):
    from backend import accounts, ms_tokens
    acc = _ms_account()
    ms.fail_network = True
    with pytest.raises(ms_tokens.Unavailable):
        ms_tokens.access_token(acc)
    assert accounts.get_own("alice", acc["id"])["status"] == "ok"
    ms.fail_network = False
    assert ms_tokens.access_token(acc) == "AT-1"


def test_ohne_app_kein_token(ms, clock):
    from backend import ms_tokens
    with pytest.raises(ms_tokens.Expired):
        ms_tokens.access_token(_ms_account())
    assert ms.calls == []


def test_neu_anmelden_setzt_zurueck(ms, clock, app_set):
    from backend import ms_tokens
    acc = _ms_account()
    ms.token.append(err("invalid_grant"))
    with pytest.raises(ms_tokens.Expired):
        ms_tokens.access_token(acc)
    ms_tokens.store(acc["id"], {"access_token": "AT-5", "refresh_token": "RT-5", "expires_in": 3600})
    assert ms_tokens.access_token(acc) == "AT-5" and _secret(acc["id"]) == {"refresh_token": "RT-5"}


def test_passwort_konto_gibt_keinen_refresh_token_heraus(ms, clock, app_set):
    from backend import accounts
    acc = _ms_account()
    assert accounts.password_of(acc["id"]) == "", "Refresh-Token geht nie als Passwort durch den Code"
