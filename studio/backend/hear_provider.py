"""Heraushören für die Untertitel (Spec „Bauplan 6b“): OpenRouter /audio/transcriptions mit Zeiten je Abschnitt.

Der Kern-Baustein (tools/_openrouter_transcribe) liefert nur Text ohne Zeiten, daher hier eine eigene Fassung mit
`response_format=verbose_json` und `timestamp_granularities[]=segment`. Die Sprache wird immer mitgeschickt (ohne
erkannte Whisper in der Probe Deutsch als Englisch). Fehler tragen nur einen Code.
"""
from __future__ import annotations

import logging
from pathlib import Path

import httpx

logger = logging.getLogger("hhmod_studio.hear")

URL = "https://openrouter.ai/api/v1/audio/transcriptions"
TIMEOUT = 600.0
KEYS = ("start", "end", "text", "no_speech_prob")
# Modelle mit brauchbaren Zeiten je Satz (Probe 18.10.). whisper-1 liefert nur EINEN Abschnitt über den ganzen Ton.
SEGMENT_MODELS = ("openai/whisper-large-v3", "openai/whisper-large-v3-turbo")
DEFAULT_MODEL = SEGMENT_MODELS[0]


class ProviderError(RuntimeError):
    """Fehlercode: no_key, provider_rejected, provider_unreachable, empty_answer."""


def server_model() -> str:
    from hydrahive.llm.media_models import get_media_model
    return get_media_model("transcribe")


def model_for_subtitles() -> str:
    """Server-Standard, wenn er Zeiten je Satz liefert oder lokal ist (dann lehnt der Start ab – nicht heimlich in die
    Cloud); sonst ein Cloud-Modell mit Zeiten beim selben Anbieter."""
    m = server_model()
    return m if m in SEGMENT_MODELS or is_local(m) else DEFAULT_MODEL


def is_local(model: str) -> bool:
    from hydrahive.llm.local_voice import is_local as _local
    return _local(model) or model.startswith("local/")


def transcribe(path: Path, language: str, model: str) -> list[dict]:
    """Abschnitte [{start, end, text, no_speech_prob}] aus der Antwort. Wirft ProviderError."""
    from hydrahive.llm._config import openrouter_key
    key = openrouter_key()
    if not key:
        raise ProviderError("no_key")
    data = {"model": model, "language": language, "response_format": "verbose_json", "timestamp_granularities[]": "segment"}
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.post(URL, headers={"Authorization": f"Bearer {key}"}, data=data,
                               files={"file": (path.name, path.read_bytes(), "audio/mp4")})
    except httpx.HTTPError as e:
        raise ProviderError("provider_unreachable") from e
    if resp.status_code >= 400:
        logger.info("Studio-Heraushören: Anbieter lehnt ab (%s, %s): %s", model, resp.status_code, resp.text[:300])
        raise ProviderError("provider_rejected")
    try:
        segments = resp.json().get("segments")
    except ValueError as e:
        raise ProviderError("empty_answer") from e
    if not isinstance(segments, list) or not segments:
        raise ProviderError("empty_answer")
    return [{k: s.get(k) for k in KEYS if k in s} for s in segments if isinstance(s, dict)]
