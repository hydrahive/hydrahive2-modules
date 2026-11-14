"""Text-LLM für den Storyteller über das Agenten-Template (Kern: Plan E5 agent-templates).

Hat das Buch bzw. der Aufruf ein eigenes Modell, gilt es wie bisher. Sonst fragt der Storyteller die Rolle
`storyteller-ghostwriter` an (Manifest-Template, Kopie von `modul-schreiber`) und bekommt Kette + Failover.
Ein älterer Kern ohne `template=` (kein `SUPPORTS_TEMPLATE`) nimmt das Standardmodell wie früher.
"""
from __future__ import annotations

from collections.abc import AsyncIterator

from hydrahive.llm import client as _client

TEMPLATE = "storyteller-ghostwriter"


def _kw(model: str | None) -> dict:
    if model or not getattr(_client, "SUPPORTS_TEMPLATE", False):
        return {}
    return {"template": TEMPLATE}


async def complete(messages: list[dict], model: str | None = None,
                   temperature: float = 0.7, max_tokens: int = 4096) -> str:
    return await _client.complete(messages, model=model, temperature=temperature, max_tokens=max_tokens, **_kw(model))


def stream(messages: list[dict], model: str | None = None,
           temperature: float = 0.7, max_tokens: int = 4096) -> AsyncIterator[str]:
    return _client.stream(messages, model=model, temperature=temperature, max_tokens=max_tokens, **_kw(model))
