from __future__ import annotations

from datetime import UTC, datetime, timedelta

from . import job_store
from .job_store import JobRecord
from .sab_credentials import resolve_sab_connection
from .sab_status import find_handoff


def _stamp(value: datetime) -> str:
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


async def reconcile_job(
    username: str, job: JobRecord, *, now: datetime | None = None
) -> JobRecord:
    moment = now or datetime.now(UTC)
    if job.state == "claimed_prewrite":
        if _parse(job.state_changed_at) + timedelta(minutes=15) > moment:
            return job
        recovered = job_store.transition(
            username, job.result_id, job.claim_token, expected="claimed_prewrite",
            target="available", now=_stamp(moment), error_code="claim_lease_expired",
        )
        return recovered or job_store.get(username, job.result_id) or job
    if job.state == "submitting":
        job = job_store.transition(
            username, job.result_id, job.claim_token, expected="submitting",
            target="uncertain", now=_stamp(moment), error_code="sab_handoff_uncertain",
            uncertain_until=_stamp(moment + timedelta(hours=24)),
        ) or job
    if job.state != "uncertain":
        return job
    found = await find_handoff(resolve_sab_connection(username), job.handoff_id)
    if found:
        return job_store.transition(
            username, job.result_id, job.claim_token, expected="uncertain",
            target="consumed", now=_stamp(moment), sab_job_id=found,
        ) or job
    if job.uncertain_until and _parse(job.uncertain_until) <= moment:
        return job_store.transition(
            username, job.result_id, job.claim_token, expected="uncertain",
            target="manual_review_required", now=_stamp(moment),
            error_code="sab_reconciliation_timeout",
        ) or job
    return job
