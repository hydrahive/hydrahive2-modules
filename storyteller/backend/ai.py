"""Storyteller — KI-Vorschlag (Spec 1b §4). Ändert NICHTS am Buch; liefert nur Text zurück."""
from __future__ import annotations

import re
import time
from collections import defaultdict, deque

from hydrahive.llm.client import complete

from . import storage
from ._names import KIND_LABEL, LANGUAGE_LABEL

ACTIONS = ("rewrite", "expand", "shorten", "continue")
MAX_SELECTION = 8000
MAX_TOKENS = 2000
RATE_PER_MINUTE = 20
_BEFORE, _AFTER = 2000, 500

_INSTRUCTION = {
    "rewrite": "Formuliere den markierten Text neu: gleicher Inhalt, besserer Fluss, gleiche Länge.",
    "expand": "Baue den markierten Text aus: mehr Details, Sinneseindrücke, etwa doppelt so lang. Nichts Neues erfinden, was der Geschichte widerspricht.",
    "shorten": "Kürze den markierten Text auf etwa die Hälfte. Inhalt und Ton bleiben.",
    "continue": "Schreibe ab der markierten Stelle 1–3 Absätze weiter, passend zu Handlung, Figuren und Ton.",
}

_rate: dict[str, deque] = defaultdict(deque)
_busy: set[tuple[str, str]] = set()  # (Nutzer, Buch) mit laufender Anfrage


class AiError(Exception):
    def __init__(self, code: str, message: str, status: int):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def acquire(user: str, book_id: str) -> tuple[str, str]:
    """Gemeinsame Sperre + Drosselung für alle KI-Läufe eines Buchs (Vorschlag, Ghostwriter).
    Gibt den Schlüssel zurück; der Aufrufer gibt ihn mit release() frei."""
    key = (user, book_id)
    if key in _busy:
        raise AiError("ai_busy", "Für dieses Buch läuft schon eine KI-Anfrage – bitte warten.", 409)
    _check_rate(user)
    _busy.add(key)
    return key


def release(key: tuple[str, str]) -> None:
    _busy.discard(key)


def _check_rate(user: str) -> None:
    now = time.monotonic()
    q = _rate[user]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= RATE_PER_MINUTE:
        raise AiError("rate_limited", "Zu viele KI-Anfragen – bitte eine Minute warten.", 429)
    q.append(now)


def _context(project_id: str, book_id: str, scene_id: str, selection: str, action: str = "rewrite") -> tuple[str, str]:
    """Bei „continue“ ist ``selection`` der Text direkt vor dem Cursor (Anker): weitergeschrieben
    wird hinter ihm; ohne Anker oder wenn er nicht (mehr) vorkommt, am Ende der Szene."""
    book = storage.get_book(project_id, book_id)
    st = storage.get_structure(project_id, book_id)
    scene = storage.get_scene(project_id, book_id, scene_id)
    order = [s for p in st["parts"] for c in p["chapters"] for s in c["scenes"]]
    i = order.index(scene_id) if scene_id in order else 0
    prev = [storage.get_scene(project_id, book_id, s) for s in order[max(0, i - 2):i]]
    text = scene["text"]
    found = text.rfind(selection) if selection else -1
    if action == "continue":
        cut = found + len(selection) if found >= 0 else len(text)
        before, after, selection = text[max(0, cut - _BEFORE):cut], text[cut:cut + _AFTER], ""
    else:
        at = found if found >= 0 else len(text)
        before, after = text[max(0, at - _BEFORE):at], text[at + len(selection):at + len(selection) + _AFTER]
    lower = text.lower()
    people = [e for e in st.get("entities", []) if any(
        n and re.search(rf"(?<!\w){re.escape(n.lower())}(?!\w)", lower) for n in [e["name"], *e.get("aliases", [])])]
    lang = LANGUAGE_LABEL.get(book["language"], book["language"])
    system = (f"Du bist Lektor und Co-Autor für ein Buch. Art: {KIND_LABEL.get(book['kind'], book['kind'])}. "
              f"Sprache: {lang}. Zielgruppe: {book.get('audience') or 'nicht angegeben'}. "
              f"Antworte ausschließlich mit dem neuen Text auf {lang}: keine Überschrift, kein Vorspann wie "
              f"„Hier ist …“, keine Erklärung, keine Anführungszeichen drumherum. Dein Text wird unverändert eingesetzt.")
    parts = []
    if book.get("idea"):
        parts.append(f"Worum es im Buch geht: {book['idea']}")
    earlier = [f"- {p['title']}: {p['summary']}" for p in prev if p.get("summary")]
    if earlier:  # ohne Zusammenfassungen keine leere Überschrift
        parts.append("Was vorher geschah:\n" + "\n".join(earlier))
    if people:
        parts.append("Steckbriefe:\n" + "\n".join(
            f"- {e['name']}: {e.get('description', '')} " + "; ".join(f"{f['key']}: {f['value']}" for f in e.get("fields", []))
            for e in people))
    parts.append(f"Text davor:\n{before}" if before else "Die Szene beginnt hier.")
    parts.append(f"MARKIERTER TEXT:\n{selection}" if selection else "Weiterschreiben ab hier.")
    if after:
        parts.append(f"Text danach:\n{after}")
    return system, "\n\n".join(parts)


_LEAD_HEADING = re.compile(r"^\s*#{1,6}[^\n]*\n+")
_LEAD_LABEL = re.compile(r"^\s*(?:\*\*)?(?:hier ist|here is|gekürzte|überarbeitete|ausgebaute|neue|fortsetzung|vorschlag|"
                         r"rewritten|shortened|expanded|continuation|revised)[^\n]{0,80}:(?:\*\*)?\s*\n+", re.IGNORECASE)


def clean_proposal(raw: str) -> str:
    """Denkblöcke und typischen Vorspann entfernen (Überschrift „# Gekürzte Fassung“, „Hier ist …:“).
    Der Vorschlag wird 1:1 in die Szene eingesetzt – so etwas darf dort nicht landen."""
    text = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    for _ in range(2):
        text = _LEAD_LABEL.sub("", _LEAD_HEADING.sub("", text, count=1), count=1).strip()
    if len(text) > 1 and text[0] == text[-1] and text[0] in "\"'":
        text = text[1:-1].strip()
    return text


async def suggest(user: str, project_id: str, book_id: str, scene_id: str, action: str,
                  selection: str, model: str | None) -> dict:
    system, prompt = _context(project_id, book_id, scene_id, selection, action)
    use_model = model or storage.get_book(project_id, book_id).get("model") or None
    messages = [{"role": "system", "content": system}, {"role": "user", "content": f"{prompt}\n\nAUFGABE: {_INSTRUCTION[action]}"}]
    key = acquire(user, book_id)
    try:
        out = await complete(messages, model=use_model, temperature=0.7, max_tokens=MAX_TOKENS)
    except Exception as exc:  # Modell-/Schlüssel-/Netzfehler lesbar an die Oberfläche geben
        raise AiError("llm_failed", str(exc)[:300] or exc.__class__.__name__, 502) from exc
    finally:
        release(key)
    proposal = clean_proposal(out or "")
    if not proposal:
        raise AiError("llm_empty", "Das Modell hat keinen Text geliefert.", 502)
    return {"proposal": proposal, "model": use_model or ""}
