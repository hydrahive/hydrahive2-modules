"""REST-Routen der Zerlege-Werkstatt."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded

from . import analysis_types, artifacts, intake, jobs, reports, runtime, store, uploads
from .access import require_project
from .models import AnalyzeIn, CaseIn

router = APIRouter()
Auth = Annotated[tuple[str, str], Depends(require_auth)]


def _owned_case(case_id: str, auth: Auth, *, required: str = "read") -> dict:
    """Fall laden und Projektzugriff prüfen; fremde Fälle bleiben unsichtbar."""
    case = store.get_case(case_id)
    if not case:
        raise coded(404, "reverse_case_not_found")
    require_project(*auth, case["project_id"], required=required)
    return case


@router.post("/cases", status_code=status.HTTP_201_CREATED)
def create_case(body: CaseIn, auth: Auth) -> dict:
    require_project(*auth, body.project_id, required="write")
    if not body.authorized:
        raise coded(400, "reverse_authorization_required")
    return store.create_case(auth[0], body)


@router.get("/cases")
def list_cases(
    auth: Auth,
    project_id: Annotated[str, Query(pattern=r"^[A-Za-z0-9-]{8,64}$")],
) -> list[dict]:
    require_project(*auth, project_id)
    return store.list_cases(project_id)


@router.post("/cases/{case_id}/artifacts", status_code=status.HTTP_201_CREATED)
async def upload_artifacts(
    case_id: str,
    auth: Auth,
    files: Annotated[list[UploadFile], File()],
) -> dict:
    _owned_case(case_id, auth, required="write")
    if not files:
        raise coded(400, "reverse_artifact_empty")
    if len(files) > uploads.MAX_FILES_PER_REQUEST:
        raise coded(400, "reverse_artifact_too_many")
    if any(upload.size is None for upload in files):
        raise coded(400, "reverse_artifact_size_unknown")
    if any(upload.size > artifacts.MAX_ARTIFACT_BYTES for upload in files):
        raise coded(413, "reverse_artifact_too_large")
    results = []
    for upload in files:
        result = await uploads.store_upload(case_id, upload)
        if result["ok"]:
            try:
                store.add_artifact(case_id, result)
            except Exception:
                uploads.discard_upload(case_id, result)
                raise
        results.append(result)
    return {"files": results}


@router.post("/cases/{case_id}/intake/scan")
def scan_intake(case_id: str, auth: Auth) -> dict:
    """Projekt-Samba-Eingang prüfen und neue Dateien in den Fall übernehmen."""
    case = _owned_case(case_id, auth, required="write")
    result = intake.scan_intake(case["project_id"], case_id)
    for item in result["files"]:
        if item["ok"]:
            store.add_artifact(case_id, item)
    return result


@router.get("/cases/{case_id}/intake")
def intake_info(case_id: str, auth: Auth) -> dict:
    """Eingangsordner des Falls und seinen Projektpfad nennen."""
    case = _owned_case(case_id, auth)
    root = intake.intake_root(case["project_id"], case_id)
    return {
        "path": f"zerlegewerkstatt/eingang/{case_id}",
        "exists": root.is_dir(),
        "files": sorted(entry.name for entry in root.iterdir()
                        if not entry.name.startswith(".")) if root.is_dir() else [],
    }


@router.post("/cases/{case_id}/analyze", status_code=status.HTTP_202_ACCEPTED)
def start_analysis(case_id: str, auth: Auth, body: AnalyzeIn) -> dict:
    """Analyse eines Artefakts in der isolierten Umgebung starten."""
    _owned_case(case_id, auth, required="write")
    artifact = store.get_artifact(body.artifact_id)
    if not artifact or artifact["case_id"] != case_id:
        raise coded(404, "reverse_artifact_not_found")
    if not analysis_types.is_allowed(artifact["kind"], body.analysis_type):
        raise coded(400, "reverse_analysis_type_not_allowed")
    try:
        job = store.create_job(case_id, body.artifact_id, body.analysis_type)
    except ValueError:
        raise coded(409, "reverse_job_already_running") from None
    jobs.get_runner().start()
    return job


@router.get("/cases/{case_id}/report")
def get_report(case_id: str, auth: Auth) -> dict:
    """Bericht einer Fallakte lesen."""
    case = _owned_case(case_id, auth)
    return reports.build_report(case)


@router.get("/runtime/status")
def runtime_status(auth: Auth) -> dict:
    """Zustand der Analyseumgebung."""
    status = runtime.IncusRuntime().status()
    return {
        "available": status.available,
        "running": status.running,
        "network_disabled": status.network_disabled,
        "code": status.code,
    }


@router.get("/cases/{case_id}")
def get_case(case_id: str, auth: Auth) -> dict:
    return _owned_case(case_id, auth)
