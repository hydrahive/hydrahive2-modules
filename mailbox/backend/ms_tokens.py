"""Zugriffstoken für Microsoft-Konten (PLAN-M1b).

- Refresh-Token liegt verschlüsselt im Konto (secrets.seal, an die Konto-ID gebunden) als JSON {"refresh_token": …}
- Zugriffstoken (~1 h) nur im Speicher; erneuert, wenn weniger als MARGIN übrig ist
- schickt Microsoft einen neuen Refresh-Token mit, wird er sofort gespeichert
- endgültiger Fehler (invalid_grant …) → Kontostatus auth_failed „bitte erneut anmelden“; danach wird bis zur neuen
  Anmeldung nicht mehr bei Microsoft gefragt (Abgleich-Takt und IDLE würden es sonst ständig versuchen)
- Netzfehler → Unavailable (vorläufig, Status bleibt)
"""
from __future__ import annotations

import json
import threading
import time

from hydrahive.db._utils import now_iso
from hydrahive.db.connection import db

from . import accounts, ms_app, oauth_ms, secrets

MARGIN = 300
EXPIRED_TEXT = "Microsoft-Anmeldung abgelaufen – bitte erneut mit Microsoft anmelden"
_CACHE: dict[str, tuple[str, float]] = {}      # Konto-ID → (Zugriffstoken, gültig bis)
_DEAD: set[str] = set()                        # Konten mit endgültig abgelehnter Anmeldung
_LOCK = threading.Lock()


class Expired(RuntimeError):
    """Anmeldung endgültig ungültig – nur eine neue Anmeldung hilft."""


class Unavailable(RuntimeError):
    """Microsoft gerade nicht erreichbar – später wieder versuchen."""


def _now() -> float:
    return time.monotonic()


def seal(aid: str, refresh_token: str) -> str:
    return secrets.seal(aid, json.dumps({"refresh_token": refresh_token}))


def _refresh_token(aid: str) -> str:
    with db() as c:
        r = c.execute("SELECT secret FROM module_mailbox_accounts WHERE id=? AND auth='oauth_microsoft'",
                      (aid,)).fetchone()
    if not r:
        raise Expired("kein Microsoft-Konto")
    try:
        return json.loads(secrets.open_(aid, r[0]))["refresh_token"]
    except (secrets.SecretError, ValueError, KeyError, TypeError):
        raise Expired("Anmeldedaten unlesbar") from None


def _save_refresh(aid: str, rt: str) -> None:
    with db() as c:
        c.execute("UPDATE module_mailbox_accounts SET secret=?, updated_at=? WHERE id=? AND auth='oauth_microsoft'",
                  (seal(aid, rt), now_iso(), aid))


def prime(aid: str, tokens: dict) -> None:
    """Zugriffstoken einer frischen Anmeldung merken und Sperre aufheben (noch nichts speichern)."""
    with _LOCK:
        _DEAD.discard(aid)
        _CACHE[aid] = (tokens["access_token"], _now() + int(tokens.get("expires_in") or 3600))


def store(aid: str, tokens: dict) -> None:
    """Nach einer (neuen) Anmeldung: Refresh-Token speichern, Zugriffstoken merken, Sperre aufheben."""
    _save_refresh(aid, tokens["refresh_token"])
    prime(aid, tokens)


def forget(aid: str) -> None:
    """Zugriffstoken verwerfen (z. B. vom Server abgelehnt) – beim nächsten Mal wird erneuert."""
    with _LOCK:
        _CACHE.pop(aid, None)


def access_token(acc: dict) -> str:
    aid = acc["id"]
    with _LOCK:
        if aid in _DEAD:
            raise Expired(EXPIRED_TEXT)
        hit = _CACHE.get(aid)
        if hit and hit[1] - _now() > MARGIN:
            return hit[0]
    app = ms_app.get()
    if not app["client_id"]:
        raise Expired("Microsoft-Anmeldung ist auf diesem HydraHive nicht (mehr) eingerichtet")
    try:
        t = oauth_ms.refresh(app["client_id"], app["tenant"], _refresh_token(aid))
    except oauth_ms.OAuthError as e:
        if e.code == "network" or e.code.startswith("http_5") or e.code in ("temporarily_unavailable", "server_error"):
            raise Unavailable(str(e)) from None
        with _LOCK:
            _DEAD.add(aid)
            _CACHE.pop(aid, None)
        accounts.set_status(aid, "auth_failed", EXPIRED_TEXT)
        raise Expired(EXPIRED_TEXT) from None
    if t.get("refresh_token"):
        _save_refresh(aid, t["refresh_token"])
    with _LOCK:
        _CACHE[aid] = (t["access_token"], _now() + t["expires_in"])
    return t["access_token"]
