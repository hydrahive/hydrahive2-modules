"""Tasks-Modul — FastAPI-Router."""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_auth

from . import service

router = APIRouter()

Auth = Annotated[tuple[str, str], Depends(require_auth)]


class TaskIn(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str = ""
    priority: str = "medium"
    project_id: str | None = None
    session_id: str | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None  # ersetzt; alte Fassung → Verlauf
    status: str | None = None
    priority: str | None = None
    note: str | None = None  # hängt eine datierte Notiz an


@router.get("/tasks")
def list_tasks(
    auth: Auth,
    status: str | None = None,
    project_id: str | None = None,
) -> list[dict[str, Any]]:
    tasks = service.list_tasks(auth[0], status=status, project_id=project_id)
    counts = service.history_counts(auth[0])
    return [{**t, "history_count": counts.get(t["id"], 0)} for t in tasks]


@router.post("/tasks", status_code=status.HTTP_201_CREATED)
def create_task(body: TaskIn, auth: Auth) -> dict[str, Any]:
    if body.priority not in service.VALID_PRIORITIES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Ungültige Priorität")
    return service.create_task(
        auth[0],
        title=body.title,
        description=body.description,
        priority=body.priority,
        project_id=body.project_id,
        session_id=body.session_id,
    )


@router.patch("/tasks/{task_id}")
def update_task(task_id: str, body: TaskUpdate, auth: Auth) -> dict[str, Any]:
    try:
        result = service.update_task(
            auth[0],
            task_id,
            title=body.title,
            description=body.description,
            status=body.status,
            priority=body.priority,
            note=body.note,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task nicht gefunden")
    return result


@router.get("/tasks/{task_id}/history")
def task_history(task_id: str, auth: Auth) -> list[dict[str, Any]]:
    """Frühere Fassungen von Titel/Beschreibung, neueste zuerst (Task df2f2eb2)."""
    versions = service.history(auth[0], task_id)
    if versions is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task nicht gefunden")
    return versions


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: str, auth: Auth) -> None:
    if not service.delete_task(auth[0], task_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task nicht gefunden")
