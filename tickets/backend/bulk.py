"""Permission-checked bulk ticket mutations with per-ticket results."""
from __future__ import annotations

from hydrahive.api.middleware.auth import AuthPrincipal
from hydrahive.db.connection import db

from . import service
from .models import TicketUpdate
from .permissions import can_update_ticket


def update_tickets(
    principal: AuthPrincipal,
    ticket_ids: list[str],
    update: TicketUpdate,
) -> dict[str, object]:
    if not ticket_ids or len(ticket_ids) > 100:
        raise ValueError("invalid_bulk_size")
    results: list[dict[str, str]] = []
    updated = skipped = failed = 0
    for ticket_id in dict.fromkeys(ticket_ids):
        with db() as conn:
            row = conn.execute("SELECT * FROM module_tickets WHERE id=?", (ticket_id,)).fetchone()
            allowed = row is not None and can_update_ticket(conn, row, principal)
        if row is None:
            results.append({"ticket_id": ticket_id, "status": "error", "code": "ticket_not_found"})
            failed += 1
            continue
        if not allowed:
            results.append({"ticket_id": ticket_id, "status": "skipped", "code": "ticket_update_forbidden"})
            skipped += 1
            continue
        try:
            service.update_ticket(ticket_id, update, principal)
        except service.TicketServiceError as exc:
            results.append({"ticket_id": ticket_id, "status": "error", "code": exc.code})
            failed += 1
            continue
        results.append({"ticket_id": ticket_id, "status": "updated"})
        updated += 1
    return {"updated": updated, "skipped": skipped, "failed": failed, "results": results}
