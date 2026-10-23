"""Inhalte einer Mail: Kopf + Text, bereinigtes HTML (für das sandbox-iframe), Anhänge, Roh-.eml (Spec §6/§11).

Immer erst Besitz prüfen (access.message_owned → sonst 404). Anhänge kommen als Download (octet-stream,
nosniff); nur eingebettete Rasterbilder dürfen mit ?inline=1 als Bild ausgeliefert werden (für <img> im HTML).
"""
from __future__ import annotations

import email
import email.policy
import json
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Response, status
from hydrahive.api.middleware.auth import AuthPrincipal, require_principal_or_query
from hydrahive.api.middleware.errors import coded

from . import access, archive, mime_parts, parse, sanitize

router = APIRouter()
# <iframe>/<img> können keinen Authorization-Header setzen → ?token= erlaubt (Kern: require_principal_or_query)
Auth = Annotated[AuthPrincipal, Depends(require_principal_or_query)]
_INLINE_OK = {"image/png", "image/jpeg", "image/gif", "image/webp", "image/bmp"}
_PREFIX = "/api/modules/mailbox"


def _own(user: str, mid: int) -> tuple[dict, bytes]:
    m = access.message_owned(user, mid)
    if not m:
        raise coded(status.HTTP_404_NOT_FOUND, "not_found")
    try:
        return m, archive.read(m["path"])
    except archive.ArchiveError:
        raise coded(status.HTTP_404_NOT_FOUND, "file_missing") from None


def _html(raw: bytes) -> str:
    msg = email.message_from_bytes(raw, policy=email.policy.default)
    for part in msg.walk():
        if part.get_content_type() == "text/html" and (part.get_content_disposition() or "") != "attachment":
            return parse.decode_bytes(part.get_payload(decode=True) or b"", part.get_param("charset"))
    return ""


@router.get("/messages/{mid}")
def message(mid: int, auth: Auth) -> dict:
    m, raw = _own(auth.username, mid)
    p = parse.parse(raw)
    keys = ("id", "account", "account_id", "folder", "folder_id", "folder_role", "date", "from_addr", "to_addr",
            "cc_addr", "subject", "seen", "flagged", "answered", "thread_key", "deleted_on_server", "size")
    return {**{k: m[k] for k in keys}, "text": p.body, "has_html": p.has_html,
            "attachments": json.loads(m["attachments"] or "[]"), "parse_error": m["parse_error"]}


@router.get("/messages/{mid}/html")
def message_html(mid: int, auth: Auth, images: bool = False) -> Response:
    m, raw = _own(auth.username, mid)
    att = json.loads(m["attachments"] or "[]")
    cids = {a["cid"]: f"{_PREFIX}/attachments/{mid}/{a['index']}?inline=1" for a in att if a.get("cid")}
    r = sanitize.clean(_html(raw), cid_urls=cids, allow_remote=images)
    return Response(sanitize.page(r["html"]), media_type="text/html; charset=utf-8", headers={
        "Content-Security-Policy": sanitize.csp(allow_remote=images), "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer", "Cache-Control": "private, no-store",
        "X-Mailbox-Blocked-Images": str(r["blocked_images"])})


@router.get("/attachments/{mid}/{index}")
def attachment(mid: int, index: int, auth: Auth, inline: bool = Query(False)) -> Response:
    _, raw = _own(auth.username, mid)
    parts = mime_parts.parts(raw)
    if not 0 <= index < len(parts):
        raise coded(status.HTTP_404_NOT_FOUND, "not_found")
    part = parts[index]
    data = part.get_payload(decode=True) or b""
    ctype = part.get_content_type()
    name = mime_parts.safe_name(part.get_filename() or f"anhang-{index}")
    headers = {"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store",
               "Content-Security-Policy": "default-src 'none'; sandbox"}
    if inline and ctype in _INLINE_OK:
        return Response(data, media_type=ctype, headers=headers)
    headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{quote(name)}"
    return Response(data, media_type="application/octet-stream", headers=headers)


@router.get("/messages/{mid}/eml")
def message_eml(mid: int, auth: Auth) -> Response:
    m, raw = _own(auth.username, mid)
    name = mime_parts.safe_name((m["subject"] or "mail")[:80]) + ".eml"
    return Response(raw, media_type="message/rfc822", headers={
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(name)}", "X-Content-Type-Options": "nosniff",
        "Cache-Control": "private, no-store"})
