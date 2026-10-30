"""GitHub verbinden (PLAN-L2.md Baustein 1): Device-Flow, Scope nur `public_repo`, Token verschlüsselt.

Ablauf: `start()` holt Code + Link (device_code bleibt im Speicher des Servers), `wait()` fragt im Abstand `interval`
nach, bis GitHub den Token gibt. Danach `GET /user` → Login + gewährte Rechte; mehr als `public_repo` → nicht speichern.
Der Token steht nur verschlüsselt in `module_hydralabor_github` und kommt nie in Antworten, Logs oder den Container.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import UTC, datetime

from hydrahive.db.connection import db

from . import github_api
from .github_api import GitHubError

logger = logging.getLogger(__name__)
# Client-ID der OAuth-App „HydraHive Labor“ im Konto hydrahive (Till, 30.10.). Öffentlich – beim Device-Flow gibt es
# kein Client-Secret. HH_LABOR_GITHUB_CLIENT_ID überschreibt (z. B. für eine Test-App).
CLIENT_ID = "Ov23lis4cKnscWQwA60e"
SCOPE = "public_repo"
_T = "module_hydralabor_github"
_GRANT = "urn:ietf:params:oauth:grant-type:device_code"
_ERRORS = {"expired_token": "labor_github_expired", "access_denied": "labor_github_denied"}
_now = time.monotonic
_pending: dict = {}

__all__ = ["GitHubError", "client_id", "disconnect", "start", "status", "token", "wait"]


def client_id() -> str:
    return os.environ.get("HH_LABOR_GITHUB_CLIENT_ID", "").strip() or CLIENT_ID


def _crypt():
    from hydrahive.credentials import _crypto
    from hydrahive.settings import settings
    return _crypto, settings.data_dir


async def start() -> dict:
    cid = client_id()
    if not cid:
        raise GitHubError("labor_github_not_configured")
    st, body, _ = await github_api.request("POST", "https://github.com/login/device/code",
                                           data={"client_id": cid, "scope": SCOPE})
    if st != 200 or "device_code" not in body:
        raise GitHubError("labor_github_failed")
    _pending.clear()
    _pending.update(device_code=body["device_code"], interval=int(body.get("interval", 5)),
                    until=_now() + int(body.get("expires_in", 900)))
    return {"user_code": body["user_code"], "verification_uri": body["verification_uri"],
            "expires_in": int(body.get("expires_in", 900))}


async def wait() -> dict:
    if not _pending:
        raise GitHubError("labor_github_not_started")
    try:
        while _now() < _pending["until"]:
            await asyncio.sleep(_pending["interval"])
            _, body, _ = await github_api.request("POST", "https://github.com/login/oauth/access_token", data={
                "client_id": client_id(), "device_code": _pending["device_code"], "grant_type": _GRANT})
            err = body.get("error", "")
            if body.get("access_token"):
                return await _finish(body["access_token"])
            if err == "authorization_pending":
                continue
            if err == "slow_down":
                _pending["interval"] = int(body.get("interval", _pending["interval"] + 5))
                continue
            raise GitHubError(_ERRORS.get(err, "labor_github_failed"))
        raise GitHubError("labor_github_expired")
    finally:
        _pending.clear()


async def _finish(tok: str) -> dict:
    st, user, hdr = await github_api.request("GET", f"{github_api.API}/user", token=tok)
    if st != 200 or not user.get("login"):
        raise GitHubError("labor_github_failed")
    scopes = {s.strip() for s in hdr.get("x-oauth-scopes", "").split(",") if s.strip()}
    if scopes != {SCOPE}:
        raise GitHubError("labor_github_scope")
    crypto, data_dir = _crypt()
    with db() as c:
        c.execute(f"INSERT OR REPLACE INTO {_T} (id, token_enc, login, user_id, scopes, connected_at) "
                  "VALUES (1, ?, ?, ?, ?, ?)",
                  (crypto.encrypt(tok, data_dir), user["login"], int(user.get("id", 0)), SCOPE,
                   datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")))
        c.commit()
    logger.info("Hydra-Labor: mit GitHub verbunden als %s", user["login"])
    return {"connected": True, "login": user["login"]}


def _row() -> tuple[str, str, int] | None:
    with db() as c:
        r = c.execute(f"SELECT token_enc, login, user_id FROM {_T} WHERE id = 1").fetchone()
    return (r[0], r[1], r[2]) if r and r[0] else None


def status() -> dict:
    r = _row()
    return {"connected": bool(r), "login": r[1] if r else "", "pending": bool(_pending)}


def identity() -> tuple[str, int]:
    r = _row()
    return (r[1], r[2]) if r else ("", 0)


def token() -> str:
    r = _row()
    if not r:
        return ""
    crypto, data_dir = _crypt()
    return crypto.decrypt(r[0], data_dir)


def disconnect() -> None:
    _pending.clear()
    with db() as c:
        c.execute(f"DELETE FROM {_T} WHERE id = 1")
        c.commit()
