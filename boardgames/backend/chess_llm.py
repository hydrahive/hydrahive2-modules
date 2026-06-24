"""LLM-Gegner für Schach — wählt einen Zug aus einer vorgegebenen Liste.

Bewusst *constrained*: Das Modell darf nur aus den legalen UCI-Zügen wählen, die
das Frontend (Engine = Single Source of Truth) mitschickt. Damit ist jeder
zurückgegebene Zug garantiert legal. Liegt das Modell daneben oder ist die
Antwort unbrauchbar, liefern wir `move=None` — das Frontend nutzt dann seinen
Minimax-Fallback. So crasht nichts und es wird nie ein illegaler Zug gespielt.

LLM-Call über hydrahive.llm.client.complete() (Cloud wie lokal, Key serverseitig).
Robustes Parsing nach Vorbild von deepresearch/research/llm.py.
"""
from __future__ import annotations

import json
import re

from hydrahive.llm.client import complete

_THINK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)
_UCI = re.compile(r"\b([a-h][1-8][a-h][1-8][qrbn]?)\b", re.IGNORECASE)

_SYSTEM = (
    "Du bist eine starke Schach-Engine und spielst die schwarzen Steine. "
    "Du antwortest ausschließlich mit deinem Zug, niemals mit Erklärungen."
)


def _strip_thinking(text: str) -> str:
    return _THINK.sub("", text or "").strip()


def build_prompt(fen: str, moves: list[str], history: list[str]) -> str:
    """Constrained Prompt: Stellung als Kontext, Auswahl streng aus `moves`."""
    move_list = ", ".join(moves)
    hist = " ".join(history[-12:]) if history else "(Spielbeginn)"
    return (
        f"Aktuelle Stellung (FEN): {fen}\n"
        f"Bisherige Züge (UCI): {hist}\n\n"
        f"Du bist am Zug (Schwarz). Wähle GENAU EINEN Zug aus dieser Liste "
        f"legaler Züge:\n{move_list}\n\n"
        f'Antworte nur mit JSON in dieser Form: {{"move": "<uci>"}} '
        f"— wobei <uci> exakt einer der erlaubten Züge ist."
    )


def extract_move(text: str, allowed: list[str]) -> str | None:
    """Zug aus roher LLM-Antwort lesen und gegen die erlaubte Liste prüfen.

    Reihenfolge: JSON-`move` zuerst, dann erster UCI-Token im Text. Vergleich
    case-insensitiv; zurückgegeben wird die kanonische Schreibweise aus `allowed`.
    """
    allowed_lc = {m.lower(): m for m in allowed}
    cleaned = _strip_thinking(text)
    fence = _FENCE.search(cleaned)
    payload = fence.group(1) if fence else cleaned

    # 1) Sauberes JSON {"move": "..."}
    for candidate in (payload, cleaned):
        try:
            data = json.loads(candidate.strip())
        except (ValueError, TypeError):
            data = None
        if isinstance(data, dict):
            mv = str(data.get("move", "")).strip().lower()
            if mv in allowed_lc:
                return allowed_lc[mv]

    # 2) Erster UCI-Token irgendwo im Text, der erlaubt ist
    for match in _UCI.finditer(cleaned):
        mv = match.group(1).lower()
        if mv in allowed_lc:
            return allowed_lc[mv]
    return None


async def choose_move(
    *, model: str | None, fen: str, moves: list[str], history: list[str],
) -> dict:
    """Lässt das Modell einen legalen Zug wählen.

    Returns: {"move": <uci>|None, "index": <int>|-1, "source": "llm"|"invalid"}
    Wirft NICHT bei Modell-/Parsing-Fehlern — Fallback ist Sache des Frontends.
    """
    if not moves:
        return {"move": None, "index": -1, "source": "invalid"}

    prompt = build_prompt(fen, moves, history)
    messages = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": prompt},
    ]
    try:
        raw = await complete(messages, model=model, temperature=0.2, max_tokens=64)
    except Exception:  # noqa: BLE001 — jeder LLM-Fehler → Fallback, nie ein 500
        return {"move": None, "index": -1, "source": "invalid"}

    mv = extract_move(raw or "", moves)
    if mv is None:
        return {"move": None, "index": -1, "source": "invalid"}
    return {"move": mv, "index": moves.index(mv), "source": "llm"}
