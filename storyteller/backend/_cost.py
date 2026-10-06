"""Ghostwriter – Schätzung und Kosten (Spec ghostwriter.md §4/§9.4).

Tokens werden geschätzt (Zeichen/4 bzw. Wörter × 1,6), weil ``llm.client.stream`` keine Nutzungszahlen
liefert. Preise kommen ausschließlich aus dem Kern (``hydrahive.llm._pricing``); ist ein Modell dort
unbekannt (z. B. OpenRouter, lokal, Abo-Login), gibt es keine Euro-Angabe (``None``).
"""
from __future__ import annotations

from hydrahive.llm._pricing import cost_micros as _core_cost
from hydrahive.llm._pricing import provider_from_model

_CHARS_PER_WORD = 7      # grob für deutsche Prosa inkl. Leerzeichen
_OUT_PER_WORD = 1.6      # Ausgabe-Tokens je Wort


def tokens(text: str) -> int:
    return len(text) // 4


def scene_estimate(material, *, length_words: int, chunk_words: int) -> dict:
    """Wie viele Abschnitte und Tokens eine Szene ungefähr braucht (gleiches Verfahren wie ghost.write_scene)."""
    from .ghost import _SO_FAR, MAX_SECTIONS
    sections = min(MAX_SECTIONS, -(-length_words // chunk_words))
    base_in = (len(material.system) + len(material.prompt)) // 4
    # Je Abschnitt dasselbe Material plus das bisher Geschriebene (höchstens _SO_FAR Zeichen).
    so_far = sum(min(i * chunk_words * _CHARS_PER_WORD, _SO_FAR) // 4 for i in range(sections))
    return {"sections": sections, "input_tokens": base_in * sections + so_far,
            "output_tokens": int(length_words * _OUT_PER_WORD)}


def cost_micros(model: str, *, tokens_in: int, tokens_out: int) -> int | None:
    if not model:
        return None
    return _core_cost(provider_from_model(model), model, prompt_tokens=tokens_in, completion_tokens=tokens_out,
                      cache_read_tokens=0, cache_creation_tokens=0)
