"""Gespräch mit Microsoft (PLAN-M1b): Geräte-Code anfordern, auf die Anmeldung warten, Zugriffstoken erneuern.

OAuth 2.0 Device Authorization Grant gegen login.microsoftonline.com (feste Adresse; nur das geprüfte Verzeichnis aus
ms_app steht im Pfad). Bereiche laut learn.microsoft.com „Authenticate an IMAP, POP or SMTP connection using OAuth“.
Nur httpx – keine neue Abhängigkeit. Fehlertexte nur bis zur ersten Zeile (ohne Trace-/Correlation-ID), nie Tokens.
"""
from __future__ import annotations

import re

import httpx

HOST = "https://login.microsoftonline.com"
SCOPE = "https://outlook.office.com/IMAP.AccessAsUser.All https://outlook.office.com/SMTP.Send offline_access"
DEVICE_GRANT = "urn:ietf:params:oauth:grant-type:device_code"
DEFAULT_LINK = "https://microsoft.com/devicelogin"
_LINKS = ("https://microsoft.com/", "https://www.microsoft.com/", "https://login.microsoft.com/",
          "https://login.microsoftonline.com/", "https://aka.ms/")
TIMEOUT = 20.0


class OAuthError(RuntimeError):
    def __init__(self, code: str, description: str = ""):
        self.code, self.description = code, description
        super().__init__(f"{code}: {description}" if description else code)


def _client() -> httpx.Client:
    return httpx.Client(timeout=TIMEOUT, follow_redirects=False)


def _post(tenant: str, what: str, data: dict) -> tuple[int, dict]:
    try:
        with _client() as c:
            r = c.post(f"{HOST}/{tenant}/oauth2/v2.0/{what}", data=data, headers={"Accept": "application/json"})
    except httpx.HTTPError as e:
        raise OAuthError("network", f"Microsoft nicht erreichbar: {type(e).__name__}") from None
    try:
        body = r.json()
    except ValueError:
        body = {}
    return r.status_code, body if isinstance(body, dict) else {}


def _fail(body: dict, status: int) -> OAuthError:
    """Nur der eigentliche Text: Microsoft hängt „Trace ID … Correlation ID … Timestamp“ an (mal neue Zeile, mal nicht)."""
    desc = re.split(r"\s*(?:\r?\n|Trace ID:)", str(body.get("error_description") or ""), maxsplit=1)[0]
    return OAuthError(str(body.get("error") or f"http_{status}")[:60], desc.strip()[:300])


def _tokens(body: dict) -> dict:
    at = body.get("access_token")
    if not isinstance(at, str) or not at:
        raise OAuthError("no_access_token", "Microsoft hat keinen Zugriffstoken geliefert")
    out = {"access_token": at, "expires_in": int(body.get("expires_in") or 3600)}
    if isinstance(body.get("refresh_token"), str) and body["refresh_token"]:
        out["refresh_token"] = body["refresh_token"]
    return out


def device_code(client_id: str, tenant: str) -> dict:
    st, body = _post(tenant, "devicecode", {"client_id": client_id, "scope": SCOPE})
    if st != 200 or not body.get("device_code") or not body.get("user_code"):
        raise _fail(body, st)
    link = str(body.get("verification_uri") or "")
    return {"device_code": str(body["device_code"]), "user_code": str(body["user_code"])[:32],
            "verification_uri": link if link.startswith(_LINKS) else DEFAULT_LINK,
            "expires_in": max(60, min(int(body.get("expires_in") or 900), 1800)),
            "interval": max(1, min(int(body.get("interval") or 5), 60))}


def poll(client_id: str, tenant: str, device: str) -> dict:
    """{"state": "pending" | "slow_down"} oder {"state": "done", "tokens": {...}}; alles andere ist OAuthError."""
    st, body = _post(tenant, "token", {"client_id": client_id, "grant_type": DEVICE_GRANT, "device_code": device})
    if st == 200:
        t = _tokens(body)
        if "refresh_token" not in t:
            raise OAuthError("no_refresh_token", "Microsoft hat keine dauerhafte Anmeldung erlaubt (offline_access)")
        return {"state": "done", "tokens": t}
    if body.get("error") == "authorization_pending":
        return {"state": "pending"}
    if body.get("error") == "slow_down":
        return {"state": "slow_down"}
    raise _fail(body, st)


def refresh(client_id: str, tenant: str, refresh_token: str) -> dict:
    st, body = _post(tenant, "token", {"client_id": client_id, "grant_type": "refresh_token",
                                       "refresh_token": refresh_token, "scope": SCOPE})
    if st != 200:
        raise _fail(body, st)
    return _tokens(body)
