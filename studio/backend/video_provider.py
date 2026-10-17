"""Video-Anbieter für das Studio: OpenRouter-Video-Schnittstelle (`/api/v1/videos`), Spec „Bauplan Etappe 3“, 3b.

Image-to-Video: das Startbild geht als `frame_images` mit `frame_type=first_frame` mit (ein flaches `image_url` wird
von der Schnittstelle ignoriert – Erkenntnis aus atelier/backend/video.py). Ablauf: absenden → nachfragen → laden.
Läuft synchron im Auftrags-Thread. Fehler tragen nur einen Code; den Text liefert das Frontend.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx

logger = logging.getLogger("hhmod_studio.video")

URL = "https://openrouter.ai/api/v1/videos"
MODELS_URL = "https://openrouter.ai/api/v1/videos/models"
POLL_INTERVAL = 5.0
POLL_BASE, POLL_PER_SEC, POLL_CAP = 900.0, 45.0, 2700.0     # 15 min + 45 s je Sekunde Video, höchstens 45 min
MAX_BYTES = 500 * 1024 * 1024
_KEY_HOSTS = {"openrouter.ai"}                               # nur hierhin geht der Schlüssel
_durations_cache: dict[str, list[int] | None] = {}


class ProviderError(RuntimeError):
    """Fehlercode: no_key, provider_rejected, provider_unreachable, video_failed, empty_answer, timeout, bad_url,
    too_big, bad_video."""


def _key() -> str:
    from hydrahive.llm._config import openrouter_key
    key = openrouter_key()
    if not key:
        raise ProviderError("no_key")
    return key


def server_default_model() -> str:
    from hydrahive.llm.media_models import get_media_model
    return get_media_model("video")


def submit_video(*, model: str, prompt: str, image_url: str, duration: int, aspect_ratio: str) -> str:
    key = _key()
    payload = {"model": model, "prompt": prompt, "duration": duration, "aspect_ratio": aspect_ratio,
               "frame_images": [{"type": "image_url", "image_url": {"url": image_url}, "frame_type": "first_frame"}]}
    try:
        with httpx.Client(timeout=60.0) as c:
            resp = c.post(URL, json=payload, headers={"Authorization": f"Bearer {key}"})
    except httpx.HTTPError as e:
        logger.warning("Studio-Video: Anbieter nicht erreichbar: %s", e)
        raise ProviderError("provider_unreachable") from e
    if resp.status_code >= 400:
        logger.warning("Studio-Video: Anbieter lehnt ab (%s): %s", resp.status_code, resp.text[:300])
        raise ProviderError("provider_rejected")
    rid = (resp.json() or {}).get("id") or ""
    if not rid:
        raise ProviderError("empty_answer")
    return str(rid)


def poll_budget(duration: int) -> float:
    return min(POLL_CAP, POLL_BASE + max(1, int(duration)) * POLL_PER_SEC)


def _video_url(data: dict) -> str | None:
    for u in data.get("unsigned_urls") or []:
        if isinstance(u, str) and u.startswith("https://"):
            return u
    out = data.get("output") if isinstance(data.get("output"), dict) else {}
    for v in (data.get("url"), data.get("video_url"), out.get("url"), out.get("video_url")):
        if isinstance(v, str) and v.startswith("https://"):
            return v
    return None


def wait_for_video(remote_id: str, *, duration: int) -> str:
    key = _key()
    deadline = time.monotonic() + poll_budget(duration)
    with httpx.Client(timeout=30.0) as c:
        while True:
            try:
                data = c.get(f"{URL}/{remote_id}", headers={"Authorization": f"Bearer {key}"}).json() or {}
            except (httpx.HTTPError, ValueError) as e:
                logger.warning("Studio-Video: Nachfrage fehlgeschlagen (%s): %s", remote_id, e)
                data = {}
            status = str(data.get("status") or "").lower()
            if status == "completed":
                url = _video_url(data)
                if not url:
                    raise ProviderError("empty_answer")
                return url
            if status in ("failed", "error", "cancelled"):
                logger.warning("Studio-Video: Anbieter meldet Fehler (%s): %s", remote_id, str(data.get("error"))[:300])
                raise ProviderError("video_failed")
            if time.monotonic() >= deadline:
                raise ProviderError("timeout")
            time.sleep(POLL_INTERVAL)


def _looks_like_video(head: bytes) -> bool:
    return head[4:8] == b"ftyp" or head[:4] == b"\x1aE\xdf\xa3"               # MP4/MOV bzw. WebM/MKV


def download_video(url: str, dest: Path) -> None:
    """Lädt das Video nach `dest`. Schlüssel nur an OpenRouter, nur https, höchstens MAX_BYTES; sonst keine Datei."""
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ProviderError("bad_url")
    headers = {"Authorization": f"Bearer {_key()}"} if parsed.hostname in _KEY_HOSTS else {}
    tmp = dest.with_name(dest.name + ".part")
    try:
        with httpx.Client(timeout=120.0, follow_redirects=False) as c, c.stream("GET", url, headers=headers) as resp:
            if resp.status_code >= 400:
                raise ProviderError("provider_rejected")
            size, first = 0, b""
            with tmp.open("wb") as f:
                for chunk in resp.iter_bytes():
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise ProviderError("too_big")
                    if len(first) < 16:
                        first += chunk[:16 - len(first)]
                    f.write(chunk)
        if not _looks_like_video(first):
            raise ProviderError("bad_video")
        tmp.replace(dest)
    except httpx.HTTPError as e:
        raise ProviderError("provider_unreachable") from e
    finally:
        tmp.unlink(missing_ok=True)


def allowed_durations(model: str) -> list[int] | None:
    """Erlaubte Dauern laut Modellliste des Anbieters (zwischengespeichert). None = unbekannt, dann keine Anpassung."""
    if model not in _durations_cache:
        try:
            with httpx.Client(timeout=30.0) as c:
                data = c.get(MODELS_URL, headers={"Authorization": f"Bearer {_key()}"}).json().get("data") or []
            for m in data:
                d = m.get("supported_durations")
                values = sorted({int(x) for x in d if isinstance(x, int)}) if isinstance(d, list) else []
                _durations_cache[m.get("id")] = values or None
            _durations_cache.setdefault(model, None)                 # unbekanntes Modell nicht jedes Mal neu fragen
        except (httpx.HTTPError, ValueError, ProviderError, AttributeError) as e:
            logger.info("Studio-Video: Modellliste nicht lesbar (%s) – Dauer bleibt unverändert", e)
            return None
    return _durations_cache.get(model)


def nearest(duration: int, allowed: list[int] | None) -> int:
    if not allowed:
        return duration
    return min(allowed, key=lambda d: (abs(d - duration), -d))
