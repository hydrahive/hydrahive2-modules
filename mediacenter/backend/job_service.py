from __future__ import annotations

from datetime import UTC, datetime

from . import job_store
from .reconciliation import reconcile_jobs
from .sab_credentials import resolve_sab_connection
from .sab_status import fetch_owned_status


async def list_jobs(
    username: str, mode: str, *, limit: int = 100, owner_id: str | None = None
) -> list[dict]:
    if mode not in {"queue", "history"}:
        raise ValueError("invalid_mode")
    jobs = job_store.list_owned(owner_id or username, limit=limit)
    reconciled = await reconcile_jobs(username, jobs, now=datetime.now(UTC))
    ids = {job.sab_job_id for job in reconciled if job.sab_job_id}
    statuses = (
        await fetch_owned_status(resolve_sab_connection(username), mode, ids) if ids else {}
    )
    output = []
    for job in reconciled:
        upstream = statuses.get(job.sab_job_id or "")
        local_queue = job.state in {"claimed_prewrite", "submitting", "uncertain"}
        local_history = job.state in {"manual_review_required", "expired"}
        if mode == "queue" and upstream is None and not local_queue:
            continue
        if mode == "history" and upstream is None and not local_history:
            continue
        output.append(
            {
                "result_id": job.result_id,
                "title": job.title,
                "media_type": job.media_type,
                "state": job.state,
                "sab_job_id": job.sab_job_id,
                "status": upstream["status"] if upstream else job.state,
                "progress": upstream["progress"] if upstream else None,
                "eta": upstream["eta"] if upstream else None,
                "error_code": (
                    upstream["error_code"] if upstream else job.error_code
                ),
                "updated_at": job.state_changed_at,
            }
        )
    return output[:limit]
