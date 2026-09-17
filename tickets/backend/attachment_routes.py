"""Authenticated upload and download routes for private ticket attachments."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, UploadFile, status
from fastapi.responses import FileResponse

from hydrahive.api.middleware.auth import AuthPrincipal, require_principal
from hydrahive.api.middleware.errors import coded

from . import attachments
from .service import get_ticket

router = APIRouter()
Auth = Annotated[AuthPrincipal, Depends(require_principal)]


def _error(exc: attachments.AttachmentError):
    codes = {
        "ticket_not_found": (status.HTTP_404_NOT_FOUND, "ticket_not_found"),
        "comment_not_found": (status.HTTP_404_NOT_FOUND, "comment_not_found"),
        "attachment_too_large": (status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "attachment_too_large"),
        "invalid_filename": (status.HTTP_400_BAD_REQUEST, "invalid_filename"),
        "invalid_media_type": (status.HTTP_400_BAD_REQUEST, "invalid_media_type"),
    }
    http_status, code = codes.get(exc.code, (status.HTTP_400_BAD_REQUEST, exc.code))
    return coded(http_status, code)


def _require_ticket(ticket_id: str) -> None:
    if get_ticket(ticket_id) is None:
        raise coded(status.HTTP_404_NOT_FOUND, "ticket_not_found")


@router.get("/tickets/{ticket_id}/attachments")
def list_attachments_route(auth: Auth, ticket_id: str) -> list[dict]:
    del auth
    _require_ticket(ticket_id)
    return attachments.list_attachments(ticket_id)


@router.post("/tickets/{ticket_id}/attachments", status_code=status.HTTP_201_CREATED)
async def upload_attachment_route(
    auth: Auth,
    ticket_id: str,
    file: UploadFile,
    comment_id: Annotated[str | None, Query(max_length=64)] = None,
) -> dict:
    _require_ticket(ticket_id)
    try:
        return await attachments.save_upload(ticket_id, file, auth.user_id, comment_id=comment_id)
    except attachments.AttachmentError as exc:
        raise _error(exc)


@router.get("/tickets/{ticket_id}/attachments/{attachment_id}")
def download_attachment_route(auth: Auth, ticket_id: str, attachment_id: str):
    del auth
    found = attachments.get_attachment(ticket_id, attachment_id)
    if found is None:
        raise coded(status.HTTP_404_NOT_FOUND, "attachment_not_found")
    metadata, path = found
    return FileResponse(path, media_type=metadata["media_type"], filename=metadata["original_name"])
