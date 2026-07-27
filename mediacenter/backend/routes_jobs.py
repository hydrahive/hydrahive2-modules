from __future__ import annotations

from fastapi import APIRouter, status

from hydrahive.api.middleware.errors import coded

from . import arr_client, arr_handoff, enqueue_service, job_service
from .arr_credentials import ARR_SERVICES, resolve_arr_connection
from .models import (
    ArrHandoffRequest,
    ArrHandoffResponse,
    ArrTargetsResponse,
    EnqueueRequest,
    EnqueueResponse,
    JobOut,
)
from .result_registry import RESULTS
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


@router.get("/arr/{service}/targets", response_model=ArrTargetsResponse)
async def arr_targets(auth: Auth, service: str) -> ArrTargetsResponse:
    """Qualitaetsprofile und Ordner des Zieldienstes fuer den Anlege-Dialog."""
    if service not in ARR_SERVICES:
        raise coded(status.HTTP_400_BAD_REQUEST, "arr_unknown_service")
    _rate(auth.username, "arr_targets", 10)

    async def load() -> ArrTargetsResponse:
        connection = resolve_arr_connection(auth.username, service)
        return ArrTargetsResponse(
            service=service,
            quality_profiles=await arr_client.quality_profiles(connection),
            root_folders=await arr_client.root_folders(connection),
        )

    return await _guard(load)


@router.post("/arr/handoff", response_model=ArrHandoffResponse)
async def arr_handoff_route(auth: Auth, body: ArrHandoffRequest) -> ArrHandoffResponse:
    """Uebergibt einen Suchtreffer an Radarr/Sonarr.

    Bewusst nur ueber diese Route erreichbar — es gibt kein Agent-Tool dafuer,
    weil ein Anlegen in eine grosse Bibliothek schreibt (SPEC-V3.md, E5).
    """
    _rate(auth.username, "arr_handoff", 5)
    stored = RESULTS.get(auth.user_id or auth.username, body.result_id)
    if stored is None:
        raise coded(status.HTTP_404_NOT_FOUND, "result_expired")

    async def run() -> ArrHandoffResponse:
        outcome = await arr_handoff.handoff(
            auth.username, stored.decision, body.service,
            quality_profile_id=body.quality_profile_id,
            root_folder_path=body.root_folder_path,
        )
        return ArrHandoffResponse(
            service=outcome.service, title=outcome.title,
            added=outcome.added, pushed=outcome.pushed,
        )

    return await _guard(run)
