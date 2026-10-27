"""Schnittstellen Etappe 1 (SPEC „Schnittstellen“). Einstellungen + Einlesen nur Admins; Suche, Statistik und
Vorhören für jeden mit Modul-Freigabe (prüft das Modul-Tor des Kerns: module.radiostream)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import StreamingResponse
from hydrahive.api.middleware.auth import AuthPrincipal, require_principal, require_principal_or_query
from hydrahive.api.middleware.errors import coded
from hydrahive.credentials.store import list_credentials
from pydantic import BaseModel, Field

from . import audio, library, scan_state, scanner, search, settings_store
from .smb_source import SourceError, credential_pair, open_source, parse_url

router = APIRouter()
Principal = Annotated[AuthPrincipal, Depends(require_principal)]


def _admin(p: AuthPrincipal) -> None:
    if p.role != "admin":
        raise coded(status.HTTP_403_FORBIDDEN, "radiostream_admin_only")


class SourceIn(BaseModel):
    url: str = Field(default="", max_length=500)
    credential_name: str = Field(default="", max_length=60)


def _public(src: dict | None) -> dict:
    if not src:
        return {"url": None, "credential_name": None, "state": "idle", "last_scan_started": None,
                "last_scan_finished": None, "last_scan_error": None}
    return {k: src[k] for k in ("url", "credential_name", "state", "last_scan_started", "last_scan_finished",
                                "last_scan_error")}


def _checked(body: SourceIn, p: AuthPrincipal) -> None:
    try:
        parse_url(body.url)
        credential_pair(p.username, body.credential_name)
    except SourceError as exc:
        raise coded(status.HTTP_400_BAD_REQUEST, exc.code) from None


@router.get("/settings")
def get_settings(p: Principal):
    _admin(p)
    return _public(settings_store.get())


@router.put("/settings")
def put_settings(body: SourceIn, p: Principal):
    _admin(p)
    _checked(body, p)
    return _public(settings_store.save(owner=p.username, url=body.url.strip(), credential_name=body.credential_name))


@router.post("/settings/test")
def test_settings(body: SourceIn, p: Principal):
    _admin(p)
    _checked(body, p)
    try:
        conn = open_source(body.url.strip(), p.username, body.credential_name)
    except SourceError as exc:
        raise coded(status.HTTP_502_BAD_GATEWAY, exc.code) from None
    try:
        return {"ok": True, "top_dirs": len(conn.top_dirs())}
    finally:
        conn.close()


@router.get("/credentials")
def credentials(p: Principal):
    """Eigene Safe-Einträge vom Typ Benutzer/Passwort zur Auswahl – nur Name und Adresse, nie der Wert."""
    _admin(p)
    items = [{"name": c.name, "url_pattern": c.url_pattern} for c in list_credentials(p.username) if c.type == "basic"]
    return {"items": items}


@router.post("/scan", status_code=status.HTTP_202_ACCEPTED)
def start_scan(p: Principal):
    _admin(p)
    if not settings_store.get():
        raise coded(status.HTTP_409_CONFLICT, "radiostream_not_configured")
    if scan_state.snapshot()["running"]:
        raise coded(status.HTTP_409_CONFLICT, "radiostream_scan_running")
    scanner.start_in_background()
    return {"started": True}


@router.get("/scan")
def scan_status(p: Principal):
    return scan_state.snapshot()


@router.post("/scan/cancel")
def cancel_scan(p: Principal):
    _admin(p)
    scan_state.request_cancel()
    return scan_state.snapshot()


@router.get("/tracks")
def list_tracks(p: Principal, q: str = Query("", max_length=200), artist: str = Query("", max_length=300),
                genre: str = Query("", max_length=100), format: str = Query("", max_length=10),  # noqa: A002
                year_from: int | None = Query(None, ge=0, le=3000), year_to: int | None = Query(None, ge=0, le=3000),
                state: str = Query("ok", pattern="^(ok|missing)$"), limit: int = Query(100, ge=1, le=200),
                cursor: str = Query("", max_length=1000)):
    return search.tracks(q=q, artist=artist, genre=genre, fmt=format, year_from=year_from, year_to=year_to,
                         state=state, limit=limit, cursor=cursor)


@router.get("/stats")
def get_stats(p: Principal):
    return search.stats()


@router.get("/artists")
def get_artists(p: Principal):
    return search.artists()


@router.get("/genres")
def get_genres(p: Principal):
    return search.genres()


def _range(header: str | None, size: int) -> tuple[int, int] | None:
    if not header or not header.startswith("bytes=") or "," in header:
        return None
    a, _, b = header[6:].partition("-")
    try:
        start = int(a) if a else max(size - int(b), 0)
        end = int(b) if a and b else size - 1
    except ValueError:
        return None
    if start > end or start >= size:
        return None
    return start, min(end, size - 1)


@router.get("/tracks/{track_id}/audio")
def track_audio(track_id: str, request: Request,
                p: Annotated[AuthPrincipal, Depends(require_principal_or_query)]):
    t = library.by_id(track_id)
    src = settings_store.get()
    if t is None or src is None:
        raise coded(status.HTTP_404_NOT_FOUND, "radiostream_track_not_found")
    try:
        conn = open_source(src["url"], src["owner"], src["credential_name"])
        fh = conn.open(t["rel_path"])
    except (SourceError, OSError):
        raise coded(status.HTTP_502_BAD_GATEWAY, "radiostream_track_unavailable") from None

    def _closing(gen):
        try:
            yield from gen
        finally:
            fh.close()
            conn.close()

    if t["format"] in audio.DIRECT:
        size = int(t["size"])
        rng = _range(request.headers.get("range"), size)
        start, end = rng or (0, size - 1)
        headers = {"Accept-Ranges": "bytes", "Content-Length": str(end - start + 1)}
        code = status.HTTP_200_OK
        if rng:
            headers["Content-Range"] = f"bytes {start}-{end}/{size}"
            code = status.HTTP_206_PARTIAL_CONTENT
        return StreamingResponse(_closing(audio.read_range(fh, start, end)), status_code=code,
                                 media_type=audio.DIRECT[t["format"]], headers=headers)
    return StreamingResponse(_closing(audio.transcode_mp3(fh, t["format"])), media_type="audio/mpeg")
