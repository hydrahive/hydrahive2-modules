"""Routen Senden, Vorlage, Entwürfe (PLAN-M2 Schritt 8). Aktionen: action_routes.py.

Besitz: fremde Konten, Mails und Entwürfe sind 404. Eingaben 422, Grenze 429 (Retry-After), Anhänge zu groß 413,
Versand-/Serverfehler 502 mit Fehlerart. Nach dem SMTP-Versand nur noch 200 (mit Warnung) – nie ein Fehler, der
den Nutzer zum zweiten Senden verleitet.
"""
from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status
from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded

from . import access, accounts, archive, compose, drafts, outbox, ratelimit, reply, smtp_send, sync_job
from .schemas_m2 import DraftIn

router = APIRouter()
Auth = Annotated[tuple[str, str], Depends(require_auth)]
MODES = ("new", "reply", "reply_all", "forward")
UPLOAD_CHUNK = 1024 * 1024


def own_account(user: str, aid: str) -> dict:
    acc = accounts.get_own(user, aid)
    if not acc:
        raise coded(status.HTTP_404_NOT_FOUND, "not_found")
    return acc


def _original(user: str, mid: int | None, acc: dict) -> bytes:
    m = access.message_owned(user, int(mid)) if mid is not None else None
    if not m:
        raise coded(status.HTTP_404_NOT_FOUND, "not_found")
    try:
        return archive.read(m["path"])
    except archive.ArchiveError:
        raise coded(status.HTTP_404_NOT_FOUND, "file_missing") from None


async def _read_files(files: list[UploadFile]) -> list[tuple[str, str, bytes]]:
    out, total = [], 0
    for f in files:
        buf = bytearray()
        while chunk := await f.read(UPLOAD_CHUNK):
            total += len(chunk)
            if total > compose.MAX_TOTAL:
                raise coded(413, "too_large")   # Zahl: Konstantenname je nach Starlette verschieden
            buf += chunk
        out.append((f.filename or "anhang", f.content_type or "", bytes(buf)))
    return out


def _build(user: str, acc: dict, mode: str, ref: int | None, f: dict, files: list):
    try:
        if mode == "new":
            return compose.build(acc, to=f["to"], cc=f["cc"], bcc=f["bcc"], subject=f["subject"], text=f["body"],
                                 attachments=files)
        raw = _original(user, ref, acc)
        if mode == "forward":
            return compose.forward(acc, raw, to=f["to"], cc=f["cc"], bcc=f["bcc"], text=f["body"],
                                   with_attachments=f["with_attachments"], extra_attachments=files)
        return compose.reply(acc, raw, text=f["body"], reply_all=mode == "reply_all", bcc=f["bcc"],
                             extra_attachments=files)
    except compose.ComposeError as e:
        raise coded(422, "invalid", message=str(e)) from None


@router.post("/send")
async def send(auth: Auth, account_id: Annotated[str, Form(max_length=64)],
               to: Annotated[str, Form(max_length=10_000)] = "", cc: Annotated[str, Form(max_length=10_000)] = "",
               bcc: Annotated[str, Form(max_length=10_000)] = "", subject: Annotated[str, Form(max_length=998)] = "",
               body: Annotated[str, Form(max_length=1_000_000)] = "", mode: Annotated[str, Form()] = "new",
               ref_message: Annotated[int | None, Form()] = None, with_attachments: Annotated[bool, Form()] = False,
               draft_id: Annotated[str | None, Form(max_length=64)] = None,
               files: Annotated[list[UploadFile], File()] = []) -> dict:  # noqa: B006 - FastAPI-Default
    if mode not in MODES or (mode != "new" and ref_message is None):
        raise coded(422, "invalid", message="mode/ref_message")
    acc = own_account(auth[0], account_id)
    built = _build(auth[0], acc, mode, ref_message, {"to": to, "cc": cc, "bcc": bcc, "subject": subject, "body": body,
                                                     "with_attachments": with_attachments}, await _read_files(files))
    password = accounts.password_of(acc["id"])
    try:
        res = await asyncio.to_thread(outbox.deliver, acc, password, built,
                                      allow_internal=accounts.allowed_internal_hosts(), open_imap=sync_job._open)
    except ratelimit.RateLimited as e:
        err = coded(status.HTTP_429_TOO_MANY_REQUESTS, "rate_limited", retry_after=e.retry_after)
        err.headers = {"Retry-After": str(e.retry_after)}
        raise err from None
    except smtp_send.SendError as e:
        raise coded(status.HTTP_502_BAD_GATEWAY, e.code, message=str(e)) from None
    if draft_id:
        try:
            await asyncio.to_thread(drafts.delete, auth[0], draft_id, acc, password=password, open_imap=sync_job._open)
        except Exception as e:  # noqa: BLE001 - gesendet ist gesendet
            res["warning"] = (res.get("warning") + "; " if res.get("warning") else "") + f"Entwurf: {e}"[:200]
    return res


@router.get("/compose/prefill")
def prefill(auth: Auth, account_id: str = Query(max_length=64), mode: str = Query(), ref_message: int = Query()) -> dict:
    """Vorlage für das Schreibfenster – mit derselben Logik wie beim Senden (Empfänger, Betreff, Zitat)."""
    if mode not in MODES[1:]:
        raise coded(422, "invalid", message="mode")
    acc = own_account(auth[0], account_id)
    raw = _original(auth[0], ref_message, acc)
    return reply.prefill(acc, raw, mode)


@router.get("/drafts")
def list_drafts(auth: Auth) -> list[dict]:
    from .agent_drafts import ids as agent_ids
    mine = agent_ids()
    return [{**d, "by_agent": d["id"] in mine} for d in drafts.list_for(auth[0])]


def _save(auth, body: DraftIn, draft_id: str | None) -> dict:
    acc = own_account(auth[0], body.account_id)
    try:
        return drafts.save(auth[0], acc, body.model_dump(), draft_id=draft_id,
                           password=accounts.password_of(acc["id"]), open_imap=sync_job._open)
    except drafts.DraftError as e:
        if "nicht gefunden" in str(e) or "anderen Konto" in str(e):
            raise coded(status.HTTP_404_NOT_FOUND, "not_found") from None
        raise coded(422, "invalid", message=str(e)) from None


@router.post("/drafts", status_code=status.HTTP_201_CREATED)
async def create_draft(auth: Auth, body: DraftIn) -> dict:
    return await asyncio.to_thread(_save, auth, body, None)


@router.patch("/drafts/{draft_id}")
async def update_draft(auth: Auth, draft_id: str, body: DraftIn) -> dict:
    return await asyncio.to_thread(_save, auth, body, draft_id)


@router.delete("/drafts/{draft_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_draft(auth: Auth, draft_id: str) -> Response:
    d = drafts.get(auth[0], draft_id)
    acc = accounts.get_own(auth[0], d["account_id"]) if d else None
    if not acc:
        raise coded(status.HTTP_404_NOT_FOUND, "not_found")
    await asyncio.to_thread(drafts.delete, auth[0], draft_id, acc, password=accounts.password_of(acc["id"]),
                            open_imap=sync_job._open)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
