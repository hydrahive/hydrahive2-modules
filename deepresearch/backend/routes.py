"""Deep-Research-Modul — FastAPI-Router (/api/modules/deepresearch/*)."""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_auth

from . import service
from .report import generate_report_html

# Relaxte CSP nur für das Report-Dokument: es ist self-contained (inline CSS/JS) und
# bindet externe OG-Bilder ein. Gilt ausschließlich für diese eine Response.
_REPORT_CSP = (
    "default-src 'self'; img-src * data:; style-src 'unsafe-inline'; "
    "script-src 'unsafe-inline'; font-src 'self' data:; base-uri 'none'"
)

router = APIRouter()

Auth = Annotated[tuple[str, str], Depends(require_auth)]


class RunIn(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    model: str | None = None


@router.post("/runs", status_code=status.HTTP_201_CREATED)
async def start_run(body: RunIn, auth: Auth) -> dict[str, Any]:
    run_id = await service.start_run(auth[0], body.question.strip(), body.model)
    return {"run_id": run_id}


@router.get("/runs")
def list_runs(auth: Auth) -> list[dict[str, Any]]:
    return service.list_runs(auth[0])


@router.get("/runs/{run_id}")
def get_run(run_id: str, auth: Auth) -> dict[str, Any]:
    run = service.get_run(auth[0], run_id)
    if not run:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lauf nicht gefunden")
    return run


@router.get("/runs/{run_id}/report")
def get_report(run_id: str, auth: Auth) -> HTMLResponse:
    """Liefert den präsentationsfertigen, self-contained HTML-Report."""
    run = service.get_run(auth[0], run_id)
    if not run:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lauf nicht gefunden")
    if run["status"] != "done" or not run.get("result"):
        body = (
            "<!doctype html><meta charset='utf-8'><body style='font-family:system-ui;"
            "padding:2rem;color:#666'>Report noch nicht fertig.</body>"
        )
    else:
        body = generate_report_html(run["question"], run["result"])
    return HTMLResponse(body, headers={"Content-Security-Policy": _REPORT_CSP})
