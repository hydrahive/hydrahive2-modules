"""Vitrine-Routen. Zugriff regelt das Modul-Tor (Freigabe module.vitrine, Standard nur Admin)."""
from __future__ import annotations

import datetime as dt
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse

from hydrahive.settings import settings
from renderer import calendar, config, inbox, program
from renderer import preview as display_preview

from . import state, videos
from .schemas import Config, MessageIn, PreviewIn, SimulateIn

router = APIRouter()


def data_dir():
    return settings.data_dir / "vitrine"


def _fail(e: videos.VideoError):
    raise HTTPException(status_code=e.status, detail={"code": e.code})


@router.get("/status")
def get_status() -> dict:
    return {**state.read(data_dir()), **state.program_info(data_dir())}


@router.get("/config")
def get_config() -> dict:
    return config.load(data_dir())


@router.put("/config")
def put_config(body: Config) -> dict:
    data = body.dump()
    config.save(data_dir(), data)
    return data


@router.get("/templates")
def get_templates() -> list[dict]:
    return calendar.TEMPLATES


@router.post("/simulate")
def simulate(body: SimulateIn) -> dict:
    try:
        at = dt.datetime.fromisoformat(body.at)
    except ValueError:
        raise HTTPException(status_code=422, detail={"code": "vitrine_bad_datetime"}) from None
    p = program.current(data_dir(), config.load(data_dir()), at)
    return {"video": p.video.name if p.video else None, "rule": p.rule, "holiday": p.holiday, "night": p.night}


@router.post("/preview")
def start_preview(body: PreviewIn) -> dict:
    """Display zeigt 30 s das Programm dieses Zeitpunkts (Video, Feiertag, Nacht); Uhr und Status bleiben echt."""
    raw = display_preview.start(data_dir(), dt.datetime.fromisoformat(body.at))
    return {"at": raw["at"], "seconds": display_preview.SECONDS}


@router.delete("/preview", status_code=status.HTTP_204_NO_CONTENT)
def stop_preview() -> Response:
    display_preview.stop(data_dir())
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/videos")
def list_videos() -> list[dict]:
    return videos.listing(data_dir() / "videos")


@router.post("/videos", status_code=status.HTTP_201_CREATED)
async def upload_video(file: Annotated[UploadFile, File()]) -> dict:
    blob = await file.read(videos.MAX_BYTES + 1)
    try:
        return {"name": videos.store(data_dir() / "videos", file.filename or "", blob)}
    except videos.VideoError as e:
        _fail(e)


@router.delete("/videos/{name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_video(name: str) -> Response:
    try:
        videos.safe_existing(data_dir() / "videos", name).unlink()
    except videos.VideoError as e:
        _fail(e)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/messages")
def list_messages() -> list[dict]:
    return inbox.active(data_dir())


@router.post("/messages", status_code=status.HTTP_201_CREATED)
def post_message(body: MessageIn) -> dict:
    try:
        return inbox.post(data_dir(), body.text, kind=body.kind, title=body.title, seconds=body.seconds, source="cockpit")
    except inbox.InboxError as e:
        raise HTTPException(status_code=422, detail={"code": "invalid", "msg": str(e)}) from e


@router.delete("/messages/{msg_id}", status_code=status.HTTP_204_NO_CONTENT)
def dismiss_message(msg_id: str) -> Response:
    if not inbox.dismiss(data_dir(), msg_id):
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/preview.jpg")
def preview() -> FileResponse:
    p = data_dir() / "preview.jpg"
    if not p.is_file():
        raise HTTPException(status_code=404, detail={"code": "vitrine_no_preview"})
    return FileResponse(p, media_type="image/jpeg", headers={"Cache-Control": "no-store"})
