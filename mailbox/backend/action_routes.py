"""Route Aktionen auf dem Server (PLAN-M2 Schritt 8): POST /messages/actions.

Mails werden je Konto gruppiert; fremde/unbekannte IDs zählen still als „übersprungen“ (keine Existenz verraten).
Je Konto eine IMAP-Verbindung. Server nicht erreichbar → 502 mit Fehlerart; das Archiv bleibt in jedem Fall.
"""
from __future__ import annotations

import asyncio
import imaplib
import ssl
from typing import Annotated

from fastapi import APIRouter, Depends, status
from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded

from . import access, accounts, actions, auth_login, index_db, sync_job
from .schemas_m2 import ActionIn

router = APIRouter()
Auth = Annotated[tuple[str, str], Depends(require_auth)]


def _by_account(user: str, ids: list[int]) -> dict[str, list[int]]:
    accs = access.accounts_map(user)
    if not accs:
        return {}
    q = ",".join("?" * len(ids))
    with index_db.connect() as c:
        rows = c.execute(f"SELECT id, account_id FROM messages WHERE id IN ({q})", ids).fetchall()
    out: dict[str, list[int]] = {}
    for mid, aid in rows:
        if aid in accs:
            out.setdefault(aid, []).append(mid)
    return out


class ServerError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _run_account(user: str, aid: str, mids: list[int], action: str, target: str | None) -> dict:
    acc = accounts.get_own(user, aid)
    if not acc:
        return {"done": 0, "skipped": len(mids)}
    password = accounts.password_of(aid)
    try:
        conn = sync_job._open(acc)
    except (ssl.SSLError, ssl.CertificateError) as e:
        raise ServerError("tls", str(e)[:200]) from None
    except OSError as e:
        raise ServerError("connect", str(e)[:200]) from None
    try:
        try:
            auth_login.imap_login(conn, acc, password)
        except imaplib.IMAP4.error as e:
            raise ServerError("auth", accounts.redact(str(e), password)[:200]) from None
        except OSError as e:              # z. B. Microsoft gerade nicht erreichbar (Token)
            raise ServerError("connect", str(e)[:200]) from None
        try:
            return actions.apply(acc, conn, action, mids, target=target)
        except (imaplib.IMAP4.error, OSError) as e:
            raise ServerError("imap", accounts.redact(str(e), password)[:200]) from None
    finally:
        try:
            conn.logout()
        except Exception:  # noqa: BLE001 - Abmelden darf nichts mehr kaputtmachen
            pass


def _run(user: str, body: ActionIn) -> dict:
    ids = list(dict.fromkeys(body.ids))
    groups = _by_account(user, ids)
    done = 0
    for aid, mids in groups.items():
        done += _run_account(user, aid, mids, body.action, body.target)["done"]
    return {"done": done, "skipped": len(ids) - done}


@router.post("/messages/actions")
async def message_actions(auth: Auth, body: ActionIn) -> dict:
    if body.action == "move" and not body.target:
        raise coded(422, "invalid", message="target")
    try:
        return await asyncio.to_thread(_run, auth[0], body)
    except actions.ActionError as e:
        raise coded(422, "invalid", message=str(e)) from None
    except ServerError as e:
        raise coded(status.HTTP_502_BAD_GATEWAY, e.code, message=str(e)) from None
