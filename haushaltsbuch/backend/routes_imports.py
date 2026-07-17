from __future__ import annotations

import json

from fastapi import APIRouter, File, Form, Header, Query, UploadFile, status

from hydrahive.api.middleware.errors import coded

from . import import_service
from .access import Principal
from .import_models import ImportComplete, ImportProfileCreate, ImportProfileUpdate, ImportReverse, ImportRowUpdate
from .import_parsers import MAX_FILE_SIZE

router = APIRouter()


@router.get("/import-profiles")
def list_profiles(principal: Principal) -> list[dict]:
    return import_service.list_profiles(principal)


@router.post("/import-profiles", status_code=status.HTTP_201_CREATED)
def create_profile(body: ImportProfileCreate, principal: Principal) -> dict:
    return import_service.create_profile(body, principal)


@router.put("/import-profiles/{profile_id}")
def update_profile(profile_id: int, body: ImportProfileUpdate, principal: Principal) -> dict:
    return import_service.update_profile(profile_id, body, principal)


@router.delete("/import-profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(profile_id: int, principal: Principal, revision: int = Query(ge=1)) -> None:
    import_service.delete_profile(profile_id, revision, principal)


async def _read_limited(file: UploadFile) -> bytes:
    chunks: list[bytes] = []
    total = 0
    try:
        while chunk := await file.read(min(1024 * 1024, MAX_FILE_SIZE + 1 - total)):
            total += len(chunk)
            if total > MAX_FILE_SIZE:
                raise coded(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "file_too_large")
            chunks.append(chunk)
    finally:
        await file.close()
    return b"".join(chunks)


@router.post("/imports", status_code=status.HTTP_201_CREATED)
async def create_import(
    principal: Principal,
    file: UploadFile = File(...),
    account_id: int = Form(..., gt=0),
    format: str = Form(default="auto"),
    mapping: str | None = Form(default=None),
    profile_id: int | None = Form(default=None),
    content_length: int | None = Header(default=None, alias="Content-Length"),
) -> dict:
    if content_length is not None and content_length > MAX_FILE_SIZE + 1024 * 1024:
        raise coded(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "file_too_large")
    import_service.validate_upload_target(account_id, principal)
    data = await _read_limited(file)
    parsed_mapping = None
    if mapping is not None:
        try:
            parsed_mapping = json.loads(mapping)
            if not isinstance(parsed_mapping, dict):
                raise ValueError
        except (json.JSONDecodeError, ValueError) as exc:
            raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid_csv_mapping") from exc
    return import_service.create_batch(
        data, file.filename, account_id, format, principal,
        mapping=parsed_mapping, profile_id=profile_id,
    )


@router.get("/imports")
def list_imports(principal: Principal) -> list[dict]:
    return import_service.list_batches(principal)


@router.get("/imports/{batch_id}")
def get_import(batch_id: int, principal: Principal) -> dict:
    return import_service.get_batch(batch_id, principal)


@router.patch("/imports/{batch_id}/rows/{row_id}")
def update_import_row(batch_id: int, row_id: int, body: ImportRowUpdate, principal: Principal) -> dict:
    return import_service.update_row(batch_id, row_id, body, principal)


@router.post("/imports/{batch_id}/complete")
def complete_import(batch_id: int, body: ImportComplete, principal: Principal) -> dict:
    return import_service.complete_batch(batch_id, body.revision, principal)


@router.post("/imports/{batch_id}/reverse")
def reverse_import(batch_id: int, body: ImportReverse, principal: Principal) -> dict:
    return import_service.reverse_batch(batch_id, body.revision, principal)
