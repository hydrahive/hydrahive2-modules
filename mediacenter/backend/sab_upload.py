from __future__ import annotations

import asyncio
import json
import re
from typing import Literal

import httpx

from .config import SAB_MAX_JSON_BYTES, SAB_TIMEOUT_SECONDS
from .errors import SabResponseError, SabUnavailable
from .sab_credentials import SabConnection
from .sabnzbd import _client

_PRIORITY = {"default": "0", "high": "1", "low": "-1"}
_JOB_ID = re.compile(r"SABnzbd_nzo_[A-Za-z0-9_-]{1,128}\Z")


def _safe_name(handoff_id: str, title: str) -> str:
    cleaned = re.sub(r"[^\w .()\-]", " ", title, flags=re.UNICODE)
    cleaned = " ".join(cleaned.split())[:80] or "download"
    return f"{handoff_id} {cleaned}"


async def upload_nzb(
    connection: SabConnection,
    nzb: bytes,
    *,
    handoff_id: str,
    title: str,
    category: str,
    priority: Literal["default", "high", "low"] = "default",
    inner_transport: httpx.AsyncBaseTransport | None = None,
    pinned_ip: str | None = None,
) -> str:
    if priority not in _PRIORITY:
        raise SabResponseError("sab_priority_invalid")
    fields = {
        "mode": "addfile",
        "output": "json",
        "cat": category,
        "priority": _PRIORITY[priority],
        "pp": "-1",
        "nzbname": _safe_name(handoff_id, title),
    }
    try:
        async with asyncio.timeout(SAB_TIMEOUT_SECONDS):
            async with _client(
                connection, inner_transport=inner_transport, pinned_ip=pinned_ip
            ) as client:
                async with client.stream(
                    "POST", f"{connection.origin}/api", data=fields,
                    files={"nzbfile": (f"{handoff_id}.nzb", nzb, "application/x-nzb")},
                ) as response:
                    if response.status_code != 200:
                        raise SabResponseError("sab_response_invalid")
                    media_type = response.headers.get("content-type", "").split(";", 1)[0]
                    if media_type.strip().lower() != "application/json":
                        raise SabResponseError("sab_content_type_invalid")
                    chunks: list[bytes] = []
                    size = 0
                    async for chunk in response.aiter_bytes():
                        size += len(chunk)
                        if size > SAB_MAX_JSON_BYTES:
                            raise SabResponseError("sab_response_too_large")
                        chunks.append(chunk)
                    body = b"".join(chunks)
            try:
                payload = json.loads(body)
            except (json.JSONDecodeError, UnicodeDecodeError):
                raise SabResponseError("sab_response_invalid") from None
            if not isinstance(payload, dict):
                raise SabResponseError("sab_response_invalid")
    except TimeoutError:
        raise SabUnavailable("sab_unavailable") from None
    except httpx.HTTPError:
        raise SabUnavailable("sab_unavailable") from None
    if payload.get("status") is not True:
        raise SabResponseError("sab_upload_rejected")
    ids = payload.get("nzo_ids")
    if not isinstance(ids, list) or len(ids) != 1 or not isinstance(ids[0], str):
        raise SabResponseError("sab_response_invalid")
    if not _JOB_ID.fullmatch(ids[0]) or connection.api_key in ids[0]:
        raise SabResponseError("sab_response_invalid")
    return ids[0]
