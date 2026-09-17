from __future__ import annotations

import pytest

from backend.attachments import (
    MAX_ATTACHMENT_BYTES,
    AttachmentError,
    get_attachment,
    save_bytes,
)
from backend.models import TicketCreate
from backend.service import create_ticket
from hydrahive.api.middleware.auth import AuthPrincipal, create_token
from hydrahive.settings import settings


def principal() -> AuthPrincipal:
    return AuthPrincipal("user-member", "member", "user")


def headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {create_token('member', 'user', 'user-member')}"}


def test_attachment_uses_random_storage_key_and_is_downloadable(ticket_db):
    ticket = create_ticket(TicketCreate(title="Anhang"), principal())
    metadata = save_bytes(ticket["id"], "report.txt", "text/plain", b"hello", principal().user_id)
    found = get_attachment(ticket["id"], metadata["id"])

    assert metadata["original_name"] == "report.txt"
    assert metadata["storage_key"] != "report.txt"
    assert "/" not in metadata["storage_key"]
    assert metadata["sha256"]
    assert found is not None
    assert found[1].read_bytes() == b"hello"


def test_path_traversal_and_oversize_are_rejected(ticket_db):
    ticket = create_ticket(TicketCreate(title="Sicherheitsprüfung"), principal())

    with pytest.raises(AttachmentError, match="invalid_filename"):
        save_bytes(ticket["id"], "../secret.txt", "text/plain", b"x", principal().user_id)
    with pytest.raises(AttachmentError, match="attachment_too_large"):
        save_bytes(
            ticket["id"], "large.bin", "application/octet-stream",
            b"x" * (MAX_ATTACHMENT_BYTES + 1), principal().user_id,
        )


def test_upload_and_download_routes_do_not_expose_storage_path(client, ticket_db):
    created = client.post(
        "/api/modules/tickets/tickets", json={"title": "Upload"}, headers=headers()
    )
    ticket_id = created.json()["id"]
    uploaded = client.post(
        f"/api/modules/tickets/tickets/{ticket_id}/attachments",
        files={"file": ("proof.txt", b"proof", "text/plain")}, headers=headers(),
    )
    attachment_id = uploaded.json()["id"]
    downloaded = client.get(
        f"/api/modules/tickets/tickets/{ticket_id}/attachments/{attachment_id}", headers=headers()
    )

    assert uploaded.status_code == 201
    assert "storage_key" in uploaded.json()
    assert str(settings.data_dir) not in uploaded.text
    assert downloaded.status_code == 200
    assert downloaded.content == b"proof"
    assert downloaded.headers["content-type"].startswith("text/plain")
