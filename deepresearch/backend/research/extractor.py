"""Schritt 3 (pro Quelle): zielgerichtete, gründliche Extraktion einer Seite zu einem Finding.

Nichts wird still verworfen (SPEC.md): Eine unlesbare Antwort wird einmal
wiederholt; bleibt sie unlesbar, zählt sie als `unreadable`. Leere Seiten und
„nicht relevant“ werden getrennt gezählt.
"""
from __future__ import annotations

from . import budgets, prompts
from .llm import ask, parse_json
from .models import Finding, RunState

_RETRY_HINT = (
    "\n\nWICHTIG: Deine letzte Antwort war kein gültiges JSON. "
    "Antworte jetzt NUR mit dem JSON-Objekt, ohne Text davor oder danach."
)


async def _ask_json(state: RunState, prompt: str) -> dict | None:
    system = prompts.SYSTEM.format(date=prompts.today_str())
    for attempt in (prompt, prompt + _RETRY_HINT):
        raw = await ask(attempt, model=state.model, system=system, max_tokens=budgets.EXTRACT)
        data = parse_json(raw, None)
        if isinstance(data, dict):
            return data
    return None


async def extract_finding(state: RunState, result: dict, text: str, image: str) -> Finding | None:
    """LLM-Extraktion. Liefert None, wenn die Seite leer, irrelevant oder unlesbar ist (jeweils gezählt)."""
    if not text.strip():
        state.empty_pages += 1
        return None
    data = await _ask_json(state, prompts.extract(state.question, result.get("title", ""), result["url"], text))
    if data is None:
        state.unreadable += 1
        return None
    summary = str(data.get("summary", "")).strip()
    if not data.get("relevant", False) or not summary:
        state.irrelevant += 1
        return None
    return Finding(
        url=result["url"],
        title=result.get("title", "") or result["url"],
        summary=summary,
        evidence=str(data.get("evidence", "")).strip(),
        image=image,
    )
