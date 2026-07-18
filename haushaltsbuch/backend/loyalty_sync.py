"""Manuelle, idempotente Loyalty-Synchronisierung mit DB-Lock und Audit."""
from __future__ import annotations

import json
import logging

from fastapi import status

from hydrahive.api.middleware.auth import AuthPrincipal
from hydrahive.api.middleware.errors import coded
from hydrahive.db.connection import db

from . import audit, loyalty_registry
from .access import membership
from .common import NOW
from .loyalty_connections import _connection_dict, _manageable
from .loyalty_persistence import SyncPayload, persist_sync
from .loyalty_receipt_persistence import persist_receipts
from .loyalty_provider import (
    InvalidProviderData,
    LoyaltyProviderAdapter,
    ProviderConnection,
    ProviderError,
    ProviderUnavailable,
)
from .loyalty_sync_errors import finish_failure

logger = logging.getLogger(__name__)
_MAX_PAGES = 100
_PAGE_SIZE = 100
_MAX_RECEIPTS = 200


async def _pages(method, context: ProviderConnection, max_items: int | None = None) -> list:
    result, cursor, seen = [], None, set()
    for _ in range(_MAX_PAGES):
        page = await method(context, cursor, _PAGE_SIZE)
        result.extend(page.items)
        if max_items is not None and len(result) >= max_items:
            return result[:max_items]
        if page.next_cursor is None:
            return result
        if page.next_cursor in seen:
            raise InvalidProviderData("pagination_loop")
        seen.add(page.next_cursor)
        cursor = page.next_cursor
    raise InvalidProviderData("pagination_limit")

async def _collect(
    adapter: LoyaltyProviderAdapter, context: ProviderConnection
) -> tuple[SyncPayload, dict]:
    capabilities = await adapter.probe(context)
    payload = SyncPayload()
    if capabilities.balance:
        payload.balance = await adapter.get_balance(context)
    if capabilities.expirations:
        payload.expirations = await adapter.list_expirations(context)
    if capabilities.partners:
        payload.partners = await adapter.list_partners(context)
    if capabilities.activities:
        payload.activities = await _pages(adapter.list_activities, context)
    if capabilities.coupons:
        payload.coupons = await _pages(adapter.list_coupons, context)
    if capabilities.receipts:
        receipt_ids = await _pages(
            adapter.list_receipts, context, max_items=_MAX_RECEIPTS
        )
        for provider_receipt_id in receipt_ids:
            payload.receipts.append(
                await adapter.get_receipt(context, provider_receipt_id)
            )
    return payload, capabilities.model_dump()

def _start(connection_id: int, principal: AuthPrincipal):
    with db(immediate=True) as conn:
        member = membership(conn, principal)
        connection = _manageable(conn, connection_id, member)
        if not connection["feature_enabled"]:
            raise coded(status.HTTP_409_CONFLICT, "loyalty_provider_disabled")
        if connection["status"] == "syncing":
            fresh = conn.execute(
                "SELECT 1 FROM module_haushaltsbuch_loyalty_sync_runs "
                "WHERE connection_id=? AND status='running' "
                "AND julianday(started_at)>julianday('now','-30 minutes') LIMIT 1",
                (connection_id,),
            ).fetchone()
            if fresh:
                raise coded(status.HTTP_409_CONFLICT, "loyalty_sync_running")
            conn.execute(
                f"UPDATE module_haushaltsbuch_loyalty_sync_runs SET status='failed',"
                f"finished_at={NOW},error_code='stale_sync_recovered' "
                "WHERE connection_id=? AND status='running'", (connection_id,),
            )
        if connection["status"] in ("reauth_required", "blocked", "disabled"):
            raise coded(status.HTTP_409_CONFLICT, f"loyalty_{connection['status']}")
        cooldown = conn.execute(
            "SELECT 1 FROM module_haushaltsbuch_loyalty_sync_runs "
            "WHERE connection_id=? AND julianday(next_allowed_attempt_at)>julianday('now') "
            "ORDER BY id DESC LIMIT 1", (connection_id,),
        ).fetchone()
        if cooldown:
            raise coded(status.HTTP_429_TOO_MANY_REQUESTS, "loyalty_rate_limited")
        adapter = loyalty_registry.get(connection["provider"])
        if adapter is None:
            raise coded(status.HTTP_503_SERVICE_UNAVAILABLE, "loyalty_provider_unavailable")
        owner = conn.execute(
            "SELECT username FROM module_haushaltsbuch_members "
            "WHERE id=? AND household_id=?",
            (connection["owner_member_id"], connection["household_id"]),
        ).fetchone()
        cursor = conn.execute(
            "INSERT INTO module_haushaltsbuch_loyalty_sync_runs"
            "(household_id,connection_id,trigger,status,cursor_before) "
            "VALUES(?,?,'manual','running',?)",
            (connection["household_id"], connection_id, connection["sync_cursor"]),
        )
        conn.execute(
            f"UPDATE module_haushaltsbuch_loyalty_connections "
            f"SET status='syncing',last_sync_at={NOW},updated_at={NOW} WHERE id=?",
            (connection_id,),
        )
        context = ProviderConnection(
            connection_id=connection_id,
            household_id=connection["household_id"],
            provider=connection["provider"],
            credential_ref=connection["credential_ref"],
            credential_owner=owner["username"],
            country_code=connection["country_code"],
            language_code=connection["language_code"],
        )
        return cursor.lastrowid, context, adapter

def _finish_success(
    run_id: int, context: ProviderConnection, payload, capabilities, actor_user_id: str
) -> dict:
    with db(immediate=True) as conn:
        connection = conn.execute(
            "SELECT * FROM module_haushaltsbuch_loyalty_connections WHERE id=?",
            (context.connection_id,),
        ).fetchone()
        counts = persist_sync(conn, connection, payload)
        receipt_counts = persist_receipts(conn, connection, payload.receipts)
        counts.fetched += receipt_counts.fetched
        counts.created += receipt_counts.created
        counts.updated += receipt_counts.updated
        counts.skipped += receipt_counts.skipped
        conn.execute(
            f"UPDATE module_haushaltsbuch_loyalty_sync_runs SET status='succeeded',"
            f"finished_at={NOW},fetched_count=?,created_count=?,updated_count=?,"
            "skipped_count=? WHERE id=? AND status='running'",
            (counts.fetched, counts.created, counts.updated, counts.skipped, run_id),
        )
        conn.execute(
            f"UPDATE module_haushaltsbuch_loyalty_connections SET status='active',"
            f"capabilities_json=?,last_success_at={NOW},last_error_code=NULL,"
            f"revision=revision+1,updated_at={NOW} WHERE id=?",
            (json.dumps(capabilities, sort_keys=True), context.connection_id),
        )
        run = conn.execute(
            "SELECT * FROM module_haushaltsbuch_loyalty_sync_runs WHERE id=?", (run_id,)
        ).fetchone()
        connection = conn.execute(
            "SELECT * FROM module_haushaltsbuch_loyalty_connections WHERE id=?",
            (context.connection_id,),
        ).fetchone()
        audit.record(
            conn, context.household_id, actor_user_id, "loyalty_connection",
            context.connection_id, "sync",
            after={"run_id": run_id, "fetched": counts.fetched, "created": counts.created},
        )
    return {"connection": _connection_dict(connection), "run": dict(run)}

async def sync_connection(connection_id: int, principal: AuthPrincipal) -> dict:
    run_id, context, adapter = _start(connection_id, principal)
    try:
        payload, capabilities = await _collect(adapter, context)
        return _finish_success(run_id, context, payload, capabilities, principal.user_id)
    except ProviderError as error:
        finish_failure(run_id, context, error)
    except Exception:
        logger.exception("Unerwarteter Loyalty-Providerfehler (connection=%s)", connection_id)
        finish_failure(run_id, context, ProviderUnavailable())
    finally:
        try:
            await adapter.disconnect(context)
        except Exception:
            logger.warning(
                "Loyalty-Provider-Bereinigung fehlgeschlagen (connection=%s)", connection_id
            )

def list_sync_runs(connection_id: int, principal: AuthPrincipal) -> list[dict]:
    with db() as conn:
        member = membership(conn, principal)
        _manageable(conn, connection_id, member)
        rows = conn.execute(
            "SELECT * FROM module_haushaltsbuch_loyalty_sync_runs "
            "WHERE connection_id=? AND household_id=? ORDER BY id DESC LIMIT 100",
            (connection_id, member["household_id"]),
        ).fetchall()
    return [dict(row) for row in rows]
