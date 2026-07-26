from __future__ import annotations

from datetime import UTC, datetime, timedelta

from . import job_store
from .job_store import JobRecord
from .sab_credentials import resolve_sab_connection
from .sab_status import find_handoffs


def _stamp(value: datetime) -> str:
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _prepare(job: JobRecord, moment: datetime) -> JobRecord:
    if job.state == "claimed_prewrite":
        if _parse(job.state_changed_at) + timedelta(minutes=15) > moment:
            return job
        return job_store.transition(
            job.owner, job.result_id, job.claim_token, expected="claimed_prewrite",
            target="available", now=_stamp(moment), error_code="claim_lease_expired",
        ) or job_store.get(job.owner, job.result_id) or job
    if job.state == "submitting":
        return job_store.transition(
            job.owner, job.result_id, job.claim_token, expected="submitting",
            target="uncertain", now=_stamp(moment), error_code="sab_handoff_uncertain",
            uncertain_until=_stamp(moment + timedelta(hours=24)),
        ) or job
    return job


async def reconcile_jobs(
    username: str, jobs: list[JobRecord], *, now: datetime | None = None
) -> list[JobRecord]:
    moment = now or datetime.now(UTC)
    prepared = [_prepare(job, moment) for job in jobs]
    uncertain = [job for job in prepared if job.state == "uncertain"]
    if not uncertain:
        return prepared
    found = await find_handoffs(
        resolve_sab_connection(username), {job.handoff_id for job in uncertain}
    )
    output = []
    for job in prepared:
        if job.state != "uncertain":
            output.append(job)
            continue
        sab_job_id = found.get(job.handoff_id)
        if sab_job_id:
            target, error = "consumed", None
        elif job.uncertain_until and _parse(job.uncertain_until) <= moment:
            target, error = "manual_review_required", "sab_reconciliation_timeout"
        else:
            output.append(job)
            continue
        output.append(job_store.transition(
            job.owner, job.result_id, job.claim_token, expected="uncertain",
            target=target, now=_stamp(moment), sab_job_id=sab_job_id,
            error_code=error,
        ) or job)
    return output


async def reconcile_job(
    username: str, job: JobRecord, *, now: datetime | None = None
) -> JobRecord:
    return (await reconcile_jobs(username, [job], now=now))[0]
