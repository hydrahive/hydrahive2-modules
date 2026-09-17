"""Safe, private file storage for internal ticket attachments."""
from __future__ import annotations

import hashlib
import os
import sqlite3
import tempfile
from pathlib import Path
from uuid import uuid4

from hydrahive.db.connection import db
from hydrahive.settings import settings

MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024


class AttachmentError(ValueError):
    """A safe, user-correctable attachment error."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _root() -> Path:
    root = (settings.data_dir / "modules" / "tickets" / "attachments").resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _safe_name(name: str) -> str:
    if not name or "\x00" in name or "/" in name or "\\" in name:
        raise AttachmentError("invalid_filename")
    name = name.strip()
    if not name or len(name) > 255:
        raise AttachmentError("invalid_filename")
    return name


def _safe_media_type(media_type: str | None) -> str:
    value = (media_type or "application/octet-stream").strip()
    if not value or len(value) > 255 or "\x00" in value:
        raise AttachmentError("invalid_media_type")
    return value


def save_bytes(
    ticket_id: str,
    original_name: str,
    media_type: str | None,
    content: bytes,
    uploaded_by: str,
    *,
    comment_id: str | None = None,
) -> dict:
    if len(content) > MAX_ATTACHMENT_BYTES:
        raise AttachmentError("attachment_too_large")
    name = _safe_name(original_name)
    content_type = _safe_media_type(media_type)
    storage_key = uuid4().hex
    root = _root()
    destination = (root / storage_key).resolve()
    if root not in destination.parents:
        raise AttachmentError("invalid_storage_key")
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=root, prefix=".upload-", delete=False) as temp:
            temp.write(content)
            temp.flush()
            os.fsync(temp.fileno())
            temp_name = temp.name
        os.replace(temp_name, destination)
        with db(immediate=True) as conn:
            if conn.execute("SELECT 1 FROM module_tickets WHERE id=?", (ticket_id,)).fetchone() is None:
                raise AttachmentError("ticket_not_found")
            if comment_id is not None and conn.execute(
                "SELECT 1 FROM module_ticket_comments WHERE id=? AND ticket_id=?",
                (comment_id, ticket_id),
            ).fetchone() is None:
                raise AttachmentError("comment_not_found")
            attachment_id = str(uuid4())
            try:
                conn.execute(
                    "INSERT INTO module_ticket_attachments "
                    "(id,ticket_id,comment_id,original_name,storage_key,media_type,size_bytes,sha256,uploaded_by) "
                    "VALUES(?,?,?,?,?,?,?,?,?)",
                    (attachment_id, ticket_id, comment_id, name, storage_key, content_type,
                     len(content), hashlib.sha256(content).hexdigest(), uploaded_by),
                )
            except sqlite3.IntegrityError as exc:
                raise AttachmentError("attachment_conflict") from exc
            row = conn.execute(
                "SELECT id,ticket_id,comment_id,original_name,storage_key,media_type,size_bytes,sha256,uploaded_by,created_at "
                "FROM module_ticket_attachments WHERE id=?", (attachment_id,),
            ).fetchone()
    except Exception:
        if destination.exists():
            destination.unlink()
        elif temp_name and Path(temp_name).exists():
            Path(temp_name).unlink()
        raise
    return dict(row)


async def save_upload(ticket_id: str, upload, uploaded_by: str, *, comment_id: str | None = None) -> dict:
    content = await upload.read(MAX_ATTACHMENT_BYTES + 1)
    return save_bytes(ticket_id, upload.filename or "", upload.content_type, content, uploaded_by, comment_id=comment_id)


def get_attachment(ticket_id: str, attachment_id: str) -> tuple[dict, Path] | None:
    with db() as conn:
        row = conn.execute(
            "SELECT id,ticket_id,comment_id,original_name,storage_key,media_type,size_bytes,sha256,uploaded_by,created_at "
            "FROM module_ticket_attachments WHERE id=? AND ticket_id=?",
            (attachment_id, ticket_id),
        ).fetchone()
    if row is None:
        return None
    root = _root()
    path = (root / row["storage_key"]).resolve()
    if root not in path.parents or not path.is_file():
        return None
    return dict(row), path


def list_attachments(ticket_id: str) -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            "SELECT id,ticket_id,comment_id,original_name,storage_key,media_type,size_bytes,sha256,uploaded_by,created_at "
            "FROM module_ticket_attachments WHERE ticket_id=? ORDER BY rowid ASC", (ticket_id,)
        ).fetchall()
    return [dict(row) for row in rows]
