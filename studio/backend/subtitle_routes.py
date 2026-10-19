"""Studio – REST für Untertitel (Spec „Bauplan Etappe 6“). Alle Routen prüfen Mitgliedschaft."""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends
from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded

from . import plan, subtitle_format, subtitle_hear, subtitle_speech, subtitles
from ._guard import guard

router = APIRouter(prefix="/projects/{project_id}/subtitles/{lang}")
Auth = Annotated[tuple[str, str], Depends(require_auth)]


def _run(fn, *args, **kw):
    try:
        return fn(*args, **kw)
    except plan.PlanError as e:
        raise coded(e.status, e.code)


@router.get("")
def get_subtitles(project_id: str, lang: str, auth: Auth) -> dict:
    guard(auth[0], project_id)
    return _run(subtitles.load, project_id, lang)


@router.put("")
def put_subtitles(project_id: str, lang: str, auth: Auth, data: Annotated[Any, Body()] = None) -> dict:
    guard(auth[0], project_id)
    return _run(subtitles.save, project_id, lang, data)


@router.post("/from-speech")
def from_speech(project_id: str, lang: str, auth: Auth, data: Annotated[Any, Body()] = None) -> dict:
    guard(auth[0], project_id)
    replace = isinstance(data, dict) and data.get("replace") is True
    return _run(subtitle_speech.from_speech, project_id, lang, replace=replace)


@router.get("/from-audio")
def hear_info(project_id: str, lang: str, auth: Auth) -> dict:
    guard(auth[0], project_id)
    return _run(subtitle_hear.info, project_id, lang)


@router.post("/from-audio", status_code=202)
def from_audio(project_id: str, lang: str, auth: Auth, data: Annotated[Any, Body()] = None) -> dict:
    guard(auth[0], project_id)
    replace = isinstance(data, dict) and data.get("replace") is True
    return _run(subtitle_hear.start, project_id, lang, replace=replace)


@router.get("/export")
def export(project_id: str, lang: str, auth: Auth, format: str = "srt") -> dict:
    """Datei als Text (der Browser speichert sie); so braucht der Abruf kein Token in der Adresse."""
    guard(auth[0], project_id)
    subs = _run(subtitles.load, project_id, lang)
    if format not in subtitle_format.FORMATS:
        raise coded(400, "studio_subtitles_invalid")
    if not subs["cues"]:
        raise coded(400, "studio_subtitles_empty")
    content = subtitle_format.srt(subs["cues"]) if format == "srt" else subtitle_format.vtt(subs["cues"])
    title = plan.get_head(project_id).get("title") or ""
    return {"filename": subtitle_format.filename(title, lang, format), "mime": subtitle_format.FORMATS[format], "content": content}
