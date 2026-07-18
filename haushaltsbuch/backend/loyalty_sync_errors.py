"""Redigierte Abbildung externer Providerfehler auf Sync- und API-Zustände."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import NoReturn

from hydrahive.api.middleware.errors import coded
from hydrahive.db.connection import db

from .common import NOW
from .loyalty_provider import (
    AuthRequired,
    ForbiddenOrBlocked,
    InvalidProviderData,
    ProviderConnection,
    ProviderError,
    ProviderUnavailable,
    RateLimited,
    SchemaChanged,
)


def _failure_state(error: ProviderError) -> tuple[int, str, str, str | None]:
    if isinstance(error, AuthRequired):
        return 409, "loyalty_reauth_required", "reauth_required", None
    if isinstance(error, ForbiddenOrBlocked):
        return 409, "loyalty_blocked", "blocked", None
    if isinstance(error, RateLimited):
        next_at = None
        if error.retry_after_seconds is not None:
            next_at = (
                datetime.now(timezone.utc) + timedelta(seconds=error.retry_after_seconds)
            ).isoformat()
        return 429, "loyalty_rate_limited", "active", next_at
    if isinstance(error, (SchemaChanged, InvalidProviderData)):
        return 502, "loyalty_provider_schema_changed", "error", None
    if isinstance(error, ProviderUnavailable):
        return 503, "loyalty_provider_unavailable", "error", None
    return 502, "loyalty_sync_failed", "error", None


def finish_failure(
    run_id: int, context: ProviderConnection, error: ProviderError
) -> NoReturn:
    http_status, api_code, connection_status, next_at = _failure_state(error)
    with db(immediate=True) as conn:
        conn.execute(
            f"UPDATE module_haushaltsbuch_loyalty_sync_runs SET status='failed',"
            f"finished_at={NOW},error_code=?,next_allowed_attempt_at=? WHERE id=?",
            (error.code, next_at, run_id),
        )
        conn.execute(
            f"UPDATE module_haushaltsbuch_loyalty_connections SET status=?,"
            f"last_error_code=?,revision=revision+1,updated_at={NOW} WHERE id=?",
            (connection_status, error.code, context.connection_id),
        )
    raise coded(http_status, api_code)
