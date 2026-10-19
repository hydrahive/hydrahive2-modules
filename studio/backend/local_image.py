"""Lokale Bildmodelle (`local:<backend>/<workflow>`, z. B. ComfyUI auf einem Rechner im Heimnetz) – Bauplan L.

Der Kern löst Modell und Workflow auf und führt den Auftrag aus (`resolve_local_workflow`, `run_local_media`); hier nur
die Übersetzung aus dem Studio-Auftrag: Text, Startwert, Vorlagen (höchstens 3), Bildgröße aus dem Format. Läuft im
Auftrags-Thread des Studios, darum mit eigenem Event-Loop. Fehler tragen nur einen Code (wie image_provider).
"""
from __future__ import annotations

import asyncio
import dataclasses
import logging
import shutil
import tempfile
from pathlib import Path

logger = logging.getLogger("hhmod_studio.local_image")

PREFIX = "local:"
SHORT_SIDE = 768                 # kürzere Seite; FLUX.2 klein braucht etwa 9 s für 1360×768 (RTX 5060 Ti)
MAX_REFERENCES = 3
TIMEOUT = 300.0


def is_local(model: str) -> bool:
    return model.startswith(PREFIX)


def _parts():
    """Bausteine des Kerns (einzeln ersetzbar in Tests)."""
    from hydrahive.llm._config import load_config
    from hydrahive.llm.video_backends import (
        VideoParams,
        resolve_local_workflow,
        run_local_media,
    )
    return resolve_local_workflow, run_local_media, VideoParams, load_config


def size_for(aspect: str) -> tuple[int, int]:
    """Breite × Höhe zum Format: kürzere Seite 768, beide auf 16 teilbar; unbekannt/„auto“ → quadratisch."""
    a, _, b = aspect.partition(":")
    try:
        w, h = float(a), float(b)
    except ValueError:
        return SHORT_SIDE, SHORT_SIDE
    if w <= 0 or h <= 0:
        return SHORT_SIDE, SHORT_SIDE
    long = round(SHORT_SIDE * max(w, h) / min(w, h) / 16) * 16
    return (long, SHORT_SIDE) if w >= h else (SHORT_SIDE, long)


def _params(cls, *, prompt: str, references: list[str], aspect_ratio: str, seed: int | None):
    width, height = size_for(aspect_ratio)
    refs = references[:MAX_REFERENCES]
    kw = {"prompt": prompt, "width": width, "height": height, "aspect_ratio": aspect_ratio, "seed": seed,
          "image_url": refs[0] if refs else None}
    if "references" in {f.name for f in dataclasses.fields(cls)}:       # älterer Kern kennt nur ein Startbild
        kw["references"] = refs
    return cls(**kw)


def request(parts, error, *, model: str, prompt: str, references: list[str], aspect_ratio: str,
            seed: int | None) -> bytes:
    resolve, run, params_cls, load_config = parts
    try:
        backend, provider = resolve(model, load_config(), "image")
    except ValueError as e:
        logger.warning("Studio-Bild lokal: %s", e)
        raise error("provider_rejected") from e
    params = _params(params_cls, prompt=prompt, references=references, aspect_ratio=aspect_ratio, seed=seed)
    dest = Path(tempfile.mkdtemp(prefix="studio-local-"))
    try:
        path = asyncio.run(run(backend, provider, model, params, dest, timeout=TIMEOUT))
        raw = Path(path).read_bytes()
    except (RuntimeError, OSError) as e:                  # OSError umfasst TimeoutError
        logger.warning("Studio-Bild lokal: %s", e)
        raise error("provider_unreachable") from e
    finally:
        shutil.rmtree(dest, ignore_errors=True)
    if not raw:
        raise error("empty_answer")
    return raw
