"""Zuspielung an Liquidsoap (PLAN-E2.md): /feed/next nennt den nächsten Titel, /feed/file/<id> liefert ihn.

Liquidsoap fragt /feed/next per request.dynamic. Die Antwort ist eine Liquidsoap-Anfrage mit Künstler und Titel
(für „Jetzt läuft“) und dem Kürzel `radiostream:<track_id>.<mp3|flac>`. Dieses Kürzel löst das eigene Protokoll im
Liquidsoap-Skript auf (service_files.py): Es lädt /feed/file/<id> MIT Feed-Schlüssel in eine Temp-Datei. Eine
normale http-URL ginge nicht, weil Liquidsoap dabei keine Kopfzeile mitschickt.
"""
from __future__ import annotations

from fastapi import APIRouter, status
from fastapi.responses import PlainTextResponse, StreamingResponse
from hydrahive.api.middleware.errors import coded

from . import audio, library, loudness, rotation, settings_store
from .smb_source import SourceError, open_source

# Geräte-Router: Der Kern hängt ihn unter /api/module-device/radiostream ein, OHNE Benutzer-Anmeldung, aber zwingend
# mit require_feed (Schlüssel + 127.0.0.1) und Rate-Limit. Unter /api/modules/… läge sonst die Anmeldung davor
# (hydratest 29.10.: Liquidsoap bekam 401).
router = APIRouter()
_MEDIA = {"mp3": "audio/mpeg", "flac": "audio/flac"}


def _q(text: str) -> str:
    return (text or "").replace("\\", "").replace('"', "'").replace("\n", " ")[:200]


@router.get("/feed/next", response_class=PlainTextResponse)
def feed_next() -> str:
    try:
        t = rotation.pick()
    except rotation.NothingToPlay:
        raise coded(status.HTTP_503_SERVICE_UNAVAILABLE, "radiostream_library_empty")
    rotation.record(t["track_id"], t["artist"], album_artist=t.get("album_artist", ""))
    ext = "flac" if t["format"] == "flac" else "mp3"
    gain = _gain(t["track_id"])
    amp = f',liq_amplify="{gain} dB"' if gain is not None else ""
    return f'annotate:artist="{_q(t["artist"] or t.get("album_artist", ""))}",title="{_q(t["title"])}"{amp}:' \
           f'radiostream:{t["track_id"]}.{ext}\n'


def _gain(track_id: str) -> float | None:
    """Fester Lautheitswert je Titel (loudness.py). Beim ersten Mal gemessen, danach aus der DB. Scheitert das Messen
    (NAS weg, Datei kaputt), läuft der Titel ohne Angleichung – nie ohne Titel."""
    t = library.by_id(track_id) or {}
    if not t.get("loudness_tried"):
        lufs = None
        src = settings_store.get()
        if src is not None:
            try:
                conn = open_source(src["url"], src["owner"], src["credential_name"])
                try:
                    with conn.open(t["rel_path"]) as fh:
                        lufs = loudness.measure(fh, t["format"])
                finally:
                    conn.close()
            except (SourceError, OSError, KeyError):
                return None                                   # NAS weg: beim nächsten Mal neu versuchen
        library.set_loudness(track_id, lufs)
        t["loudness_lufs"] = lufs
    lufs = t.get("loudness_lufs")
    return loudness.gain_for(lufs) if lufs is not None else None


@router.get("/feed/file/{track_id}")
def feed_file(track_id: str):
    t = library.by_id(track_id)
    src = settings_store.get()
    if t is None or src is None:
        raise coded(status.HTTP_404_NOT_FOUND, "radiostream_track_not_found")
    try:
        conn = open_source(src["url"], src["owner"], src["credential_name"])
        fh = conn.open(t["rel_path"])
    except (SourceError, OSError):
        raise coded(status.HTTP_502_BAD_GATEWAY, "radiostream_track_unavailable") from None

    def _gen():
        try:
            while chunk := fh.read(audio.CHUNK):
                yield chunk
        finally:
            fh.close()
            conn.close()

    return StreamingResponse(_gen(), media_type=_MEDIA.get(t["format"], "application/octet-stream"),
                             headers={"Content-Length": str(int(t["size"]))})
