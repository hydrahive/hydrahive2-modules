"""Sprach-Anbieter für das Studio (Spec „Bauplan 5c“): nutzt die Bausteine des Kerns – OpenRouter `/audio/speech`
(`_openrouter_media.synthesize_speech`, Stimmen je Modell) bzw. lokales Piper für `local/…`-Modelle. Kein eigener
HTTP-Code; Fehler tragen nur einen Code, den Text für Menschen liefert das Frontend.
"""
from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger("hhmod_studio.voice")


class ProviderError(RuntimeError):
    """Fehlercode: no_key, provider_rejected, provider_unreachable."""


def server_default_model() -> str:
    from hydrahive.llm.media_models import get_media_model
    return get_media_model("tts")


def voices(model: str) -> list[str]:
    """Stimmen des Modells (leer = unbekannt bzw. lokales Piper mit fester Stimme)."""
    from hydrahive.llm.local_voice import is_local
    from hydrahive.llm.media_models import voices_for
    if is_local(model):
        return []
    try:
        return list(asyncio.run(voices_for(model)))
    except Exception:                          # Anbieter nicht erreichbar → Auswahl leer, Standardstimme gilt
        logger.info("Studio-Sprache: Stimmen für %s nicht abrufbar", model, exc_info=True)
        return []


def synthesize(text: str, voice: str, model: str) -> tuple[bytes, str, str, str | None]:
    """(Daten, Endung, tatsächliche Stimme, Hinweis). Wirft ProviderError."""
    from hydrahive.llm._config import openrouter_key
    from hydrahive.llm.local_voice import is_local
    from hydrahive.tools._openrouter_media import synthesize_speech
    from hydrahive.voice.tts import synthesize_local
    try:
        if is_local(model):
            data, _mime = asyncio.run(synthesize_local(text, voice))
            return data, "wav", "", None
        key = openrouter_key()
        if not key:
            raise ProviderError("no_key")
        return asyncio.run(synthesize_speech(text, voice, model, key=key))
    except ProviderError:
        raise
    except RuntimeError as e:
        logger.info("Studio-Sprache: Anbieter lehnt ab (%s): %s", model, str(e)[:300])
        raise ProviderError("provider_rejected") from e
    except OSError as e:
        raise ProviderError("provider_unreachable") from e
