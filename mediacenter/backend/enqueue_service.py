from __future__ import annotations

from datetime import UTC, datetime, timedelta

from . import job_store, newznab
from .config import SAB_CATEGORIES
from .credentials import resolve_indexer_api_key
from .errors import IndexerResponseError, SabResponseError
from .job_store import JobRecord
from .reconciliation import reconcile_job
from .result_store import RESULTS
from .sab_credentials import resolve_sab_connection
from .sab_upload import upload_nzb


def _timestamp(now: datetime | None = None) -> tuple[datetime, str]:
    value = now or datetime.now(UTC)
    return value, value.isoformat(timespec="seconds").replace("+00:00", "Z")


async def enqueue_result(
    username: str,
    result_id: str,
    *,
    priority: str = "default",
    now: datetime | None = None,
) -> JobRecord:
    existing = job_store.get(username, result_id)
    if existing and existing.state != "available":
        existing = await reconcile_job(username, existing, now=now)
        if existing.state != "available":
            return existing
    claimed = RESULTS.claim(username, result_id)
    if (
        claimed is None
        or claimed.decision.decision != "eligible"
        or claimed.decision.selection_status != "ready"
    ):
        raise IndexerResponseError("result_unavailable")
    local_claim = claimed.claim_id
    release = claimed.decision.release
    moment, stamp = _timestamp(now)
    try:
        if existing:
            job = job_store.reclaim_available(username, result_id, now=stamp)
            if job is None:
                current = job_store.get(username, result_id)
                if current is not None:
                    return current
                raise IndexerResponseError("result_unavailable")
        else:
            job, _ = job_store.claim_new(
                result_id=result_id,
                owner=username,
                media_type=claimed.decision.media_type,
                title=release.title,
                category=SAB_CATEGORIES[claimed.decision.media_type],
                now=stamp,
                action_expires_at=(moment + timedelta(minutes=15)).isoformat(
                    timespec="seconds"
                ).replace("+00:00", "Z"),
            )
        indexer_key = resolve_indexer_api_key(username)
        connection = resolve_sab_connection(username)
        nzb = await newznab.fetch_nzb(indexer_key, release.guid)
    except BaseException:
        job_store.transition(
            username, result_id, job.claim_token, expected="claimed_prewrite",
            target="available", now=stamp, error_code="prewrite_failed",
        )
        RESULTS.release(username, result_id, local_claim)
        raise
    submitting = job_store.transition(
        username, result_id, job.claim_token, expected="claimed_prewrite",
        target="submitting", now=stamp,
    )
    if submitting is None:
        RESULTS.release(username, result_id, local_claim)
        raise IndexerResponseError("enqueue_conflict")
    try:
        sab_job_id = await upload_nzb(
            connection, nzb, handoff_id=job.handoff_id, title=release.title,
            category=job.category, priority=priority,
        )
    except SabResponseError as exc:
        target = "available" if exc.code == "sab_upload_rejected" else "uncertain"
        updated = job_store.transition(
            username, result_id, job.claim_token, expected="submitting",
            target=target, now=stamp, error_code=exc.code,
            uncertain_until=(moment + timedelta(hours=24)).isoformat(
                timespec="seconds"
            ).replace("+00:00", "Z") if target == "uncertain" else None,
        )
        if target == "available":
            RESULTS.release(username, result_id, local_claim)
        if updated is None:
            raise IndexerResponseError("enqueue_conflict") from exc
        raise
    except BaseException:
        job_store.transition(
            username, result_id, job.claim_token, expected="submitting",
            target="uncertain", now=stamp, error_code="sab_handoff_uncertain",
            uncertain_until=(moment + timedelta(hours=24)).isoformat(
                timespec="seconds"
            ).replace("+00:00", "Z"),
        )
        raise
    consumed = job_store.transition(
        username, result_id, job.claim_token, expected="submitting",
        target="consumed", now=stamp, sab_job_id=sab_job_id,
    )
    if consumed is None:
        raise IndexerResponseError("enqueue_conflict")
    RESULTS.consume(username, result_id, local_claim)
    return consumed
