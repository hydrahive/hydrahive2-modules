from __future__ import annotations

from fastapi import APIRouter, status

from hydrahive.api.middleware.errors import coded

from . import enqueue_service, job_service
from .models import EnqueueRequest, EnqueueResponse, JobOut
from .routes_search import Auth, _SanitizedValidationRoute, _guard, _rate

router = APIRouter(route_class=_SanitizedValidationRoute)


@router.post("/enqueue", response_model=EnqueueResponse)
async def enqueue(auth: Auth, body: EnqueueRequest) -> EnqueueResponse:
    username = auth.username
    _rate(username, "enqueue", 5)
    job = await _guard(
        lambda: enqueue_service.enqueue_result(
            username, body.result_id, priority=body.priority, owner_id=auth.user_id
        )
    )
    if job.state in {"submitting", "uncertain"}:
        raise coded(status.HTTP_409_CONFLICT, "enqueue_status_uncertain")
    if job.state == "manual_review_required":
        raise coded(status.HTTP_409_CONFLICT, "enqueue_manual_review_required")
    return EnqueueResponse(
        result_id=job.result_id,
        title=job.title,
        media_type=job.media_type,
        state=job.state,
        sab_job_id=job.sab_job_id,
        error_code=job.error_code,
    )


@router.get("/queue", response_model=list[JobOut])
async def queue(auth: Auth) -> list[JobOut]:
    username = auth.username
    _rate(username, "queue", 30)
    rows = await _guard(lambda: job_service.list_jobs(username, "queue", owner_id=auth.user_id))
    return [JobOut(**row) for row in rows]


@router.get("/history", response_model=list[JobOut])
async def history(auth: Auth) -> list[JobOut]:
    username = auth.username
    _rate(username, "history", 30)
    rows = await _guard(lambda: job_service.list_jobs(username, "history", owner_id=auth.user_id))
    return [JobOut(**row) for row in rows]
