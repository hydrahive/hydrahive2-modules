"""Clip erzeugen: Auftrag → Anbieter → Datei + Sidecar (SPEC.md §4, §5.6, M1).

Das Ergebnis wird erst angenommen, wenn ffprobe es als Audio erkennt. Sonst entsteht keine Datei. Das Sidecar hält
die Herkunft fest: Anbieter, Modell, gesendeter Prompt, Auftrag, zurückgegebener Text, Kostenhinweis, Ersteller.
"""
from __future__ import annotations

from datetime import datetime, timezone

from . import providers, storage
from ._ffprobe import probe_audio
from .library import write_sidecar
from .prompt import MusicRequest


async def generate_clip(project_id: str, model_id: str, request: dict, *, user: str) -> dict:
    req = MusicRequest.model_validate(request or {})
    model, backend = await providers.resolve(model_id)
    result = await backend.generate(model.id, req)
    clip_id = storage.new_id()
    clip = storage.clips_dir(project_id) / f"{clip_id}.{result.ext}"
    clip.write_bytes(result.audio)
    info = await probe_audio(clip)
    if info is None:
        clip.unlink(missing_ok=True)
        raise providers.ProviderError("Der Anbieter hat kein lesbares Audio geliefert.")
    created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    title = (req.description or req.style or "Clip").strip().splitlines()[0][:80]
    meta = {
        "origin": "generated", "name": title, "backend": backend.name, "model": model.id,
        "prompt": result.prompt, "request": req.model_dump(), "returned_text": result.text,
        "price_note": model.price_note, "license_note": model.license_note,
        "created_at": created, "created_by": user, **info,
    }
    write_sidecar(clip, meta)
    return {"source_rel": storage.rel_to_workspace(project_id, clip), "origin": "generated", "name": title,
            "duration": info["duration"], "model": model.id, "backend": backend.name, "prompt": result.prompt,
            "returned_text": result.text, "price_note": model.price_note, "created_at": created}
