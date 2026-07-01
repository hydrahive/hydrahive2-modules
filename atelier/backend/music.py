"""Atelier — Musik-Generierung über OpenRouter (Lyria 3, SSE-Streaming-Chat).

Eigener Client für den Atelier-Kontext (Projekt-Storage + Sidecar statt
Chat-Pfad), aber der geknackte SSE-Parser wird aus dem Core-Tool importiert
statt neu debuggt — Lyria liefert Audio als EINE mehrere-MB-Zeile, die
httpx' aiter_lines() nicht-deterministisch zerlegt (siehe read_audio_sse).

Request-Format (verifiziert, deckungsgleich mit generate_music.py):
  POST /api/v1/chat/completions
  { model, messages:[{role:"user", content}], modalities:["text","audio"],
    audio:{"format":"mp3"}, stream: true }
"""
from __future__ import annotations

import base64
import binascii
import json
from datetime import datetime, timezone

import httpx

from hydrahive.llm.media_models import get_media_model
from hydrahive.tools._openrouter_media import openrouter_key, read_audio_sse

from . import audio_profiles, storage

_URL = "https://openrouter.ai/api/v1/chat/completions"
_TIMEOUT = 180.0
_DEFAULT_MODEL = "google/lyria-3-pro-preview"


class MusicError(RuntimeError):
    """Musik-Generierung fehlgeschlagen (Key fehlt, API-Fehler, leerer Stream)."""


def build_music_prompt(scene: str, *, style_anchor: str, profiles: list[dict]) -> str:
    """Baut den vollen Musik-Prompt: Studio-Sound-Anker + Profil-Beschreibungen
    (verbatim) + Szene (das Variable, z.B. "treibender Loop für die Verfolgung").

    Reihenfolge wie bei build_prompt() im Bild-Pfad: der konsistente Teil
    (Studio-Sound, Profile) zuerst, das Variable zuletzt.
    """
    parts: list[str] = []
    if style_anchor.strip():
        parts.append(style_anchor.strip())
    for p in profiles:
        desc = (p.get("description") or "").strip()
        name = (p.get("name") or "").strip()
        if desc:
            parts.append(f"{name}: {desc}" if name else desc)
        elif name:
            parts.append(name)
    if scene.strip():
        parts.append(scene.strip())
    return ". ".join(parts)


async def generate_music(*, model: str, prompt: str) -> bytes:
    """Generiert einen Track und gibt die rohen MP3-Bytes zurück.

    Wirft MusicError bei Key-Mangel, HTTP-/API-Fehler oder leerem/unvollständigem
    Stream (kein [DONE] gesehen).
    """
    key = openrouter_key()
    if not key:
        raise MusicError("Kein OpenRouter-API-Key konfiguriert.")

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "modalities": ["text", "audio"],
        "audio": {"format": "mp3"},
        "stream": True,
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            async with client.stream(
                "POST", _URL,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json=payload,
            ) as resp:
                if resp.status_code >= 400:
                    body = (await resp.aread()).decode("utf-8", "replace")[:400]
                    raise MusicError(f"Musik-API antwortete {resp.status_code}: {body}")
                b64_parts, done = await read_audio_sse(resp)
    except httpx.HTTPError as e:
        raise MusicError(f"Netzwerkfehler bei der Generierung: {e}") from e

    if not b64_parts:
        raise MusicError("Keine Audio-Daten in der Antwort erhalten — bitte erneut versuchen.")
    if not done:
        raise MusicError("Stream vorzeitig beendet (kein [DONE]) — bitte erneut versuchen.")

    try:
        return base64.b64decode("".join(b64_parts), validate=True)
    except (ValueError, binascii.Error) as e:
        raise MusicError(f"Audio-Daten nicht dekodierbar: {e}") from e


async def generate_for_project(project_id: str, req: dict) -> dict:
    """Führt eine Musik-Generierung für ein Projekt aus. Wirft MusicError bei Fehler.

    req: { scene, profile_ids[], model? }
    Rückgabe: das Bibliotheks-Item (name, rel, prompt, model, created_at).
    """
    anchor = audio_profiles.get_music_anchor(project_id)
    chosen = _resolve_profiles(project_id, req.get("profile_ids") or [])
    model = (req.get("model") or "").strip() or get_media_model("music") or _DEFAULT_MODEL

    prompt = build_music_prompt(req.get("scene") or "", style_anchor=anchor, profiles=chosen)
    if not prompt.strip():
        raise MusicError("Prompt ist leer — Studio-Sound, Profil oder Szene angeben.")

    raw = await generate_music(model=model, prompt=prompt)

    name = storage.save_audio_bytes(project_id, raw, ext="mp3")
    created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    meta = {
        "prompt": prompt,
        "scene": req.get("scene") or "",
        "profile_ids": [p["id"] for p in chosen],
        "model": model,
        "created_at": created,
    }
    _write_sidecar(project_id, name, meta)

    return {
        "name": name,
        "rel": f"audio/{name}",
        "path": str(storage.audio_dir(project_id) / name),
        "prompt": prompt,
        "model": model,
        "created_at": created,
    }


def _resolve_profiles(project_id: str, ids: list[str]) -> list[dict]:
    out: list[dict] = []
    for pid in ids[:6]:
        p = audio_profiles.get_profile(project_id, pid)
        if p is not None:
            out.append(p)
    return out


def _write_sidecar(project_id: str, name: str, meta: dict) -> None:
    path = storage.audio_dir(project_id) / f"{name}.json"
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), "utf-8")


def scan_library(project_id: str) -> list[dict]:
    """Generierte Tracks des Projekts (neueste zuerst) + Sidecar-Metadaten."""
    out_dir = storage.audio_dir(project_id)
    items: list[dict] = []
    for track in out_dir.iterdir():
        if track.suffix.lower() != ".mp3":
            continue
        meta_path = track.with_suffix(track.suffix + ".json")
        meta = {}
        if meta_path.is_file():
            try:
                meta = json.loads(meta_path.read_text("utf-8"))
            except (json.JSONDecodeError, OSError):
                meta = {}
        items.append({
            "name": track.name,
            "rel": f"audio/{track.name}",
            "created_at": meta.get("created_at"),
            "prompt": meta.get("prompt"),
            "model": meta.get("model"),
            "profile_ids": meta.get("profile_ids") or [],
            "mtime": track.stat().st_mtime,
        })
    items.sort(key=lambda i: i["mtime"], reverse=True)
    return items


def delete_track(project_id: str, rel: str) -> bool:
    """Löscht einen Track + sein Sidecar. True bei Erfolg."""
    root = storage.atelier_root(project_id)
    track = storage.safe_under(root, rel)
    if track is None or not track.is_file() or track.parent != storage.audio_dir(project_id):
        return False
    track.unlink(missing_ok=True)
    track.with_suffix(track.suffix + ".json").unlink(missing_ok=True)
    return True
