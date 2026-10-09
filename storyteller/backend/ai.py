"""Storyteller — KI-Vorschlag (Spec 1b §4). Ändert NICHTS am Buch; liefert nur Text zurück."""
from __future__ import annotations

import asyncio
import re
import time
from collections import defaultdict, deque

from hydrahive.llm.client import complete

from . import storage
from ._names import KIND_LABEL, LANGUAGE_LABEL
from ._texts import texts
from ._think import strip_think

ACTIONS = ("rewrite", "expand", "shorten", "continue")
MAX_SELECTION = 8000
MAX_TOKENS = 2000
RATE_PER_MINUTE = 20
_BEFORE, _AFTER = 2000, 500

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


def find_selection(text: str, selection: str, occurrence: int | None) -> int:
    """Stelle der Markierung (A5a3): das ``occurrence``-te Vorkommen (0 = erstes), das die Oberfläche mitschickt.
    Ohne Angabe oder wenn es das Vorkommen nicht gibt (z. B. andere Formatierung im Markdown): das letzte wie bisher."""
    if not selection:
        return -1
    if occurrence is not None and occurrence >= 0:
        at = -1
        for _ in range(occurrence + 1):
            at = text.find(selection, at + 1)
            if at < 0:
                break
        if at >= 0:
            return at
    return text.rfind(selection)


def _context(project_id: str, book_id: str, scene_id: str, selection: str, action: str = "rewrite",
             occurrence: int | None = None) -> tuple[str, str]:
    """Bei „continue“ ist ``selection`` der Text direkt vor dem Cursor (Anker): weitergeschrieben
    wird hinter ihm; ohne Anker oder wenn er nicht (mehr) vorkommt, am Ende der Szene."""
    book = storage.get_book(project_id, book_id)
    st = storage.get_structure(project_id, book_id)
    scene = storage.get_scene(project_id, book_id, scene_id)
    order = [s for p in st["parts"] for c in p["chapters"] for s in c["scenes"]]
    i = order.index(scene_id) if scene_id in order else 0
    prev = [storage.get_scene(project_id, book_id, s) for s in order[max(0, i - 2):i]]
    text = scene["text"]
    found = find_selection(text, selection, occurrence)
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
    t = texts(book)
    system = t("editor_system", kind=KIND_LABEL.get(book["kind"], book["kind"]), lang=lang,
               audience=book.get("audience") or t("audience_none"))
    parts = []
    if book.get("idea"):
        parts.append(t("about", idea=book["idea"]))
    earlier = [f"- {p['title']}: {p['summary']}" for p in prev if p.get("summary")]
    if earlier:  # ohne Zusammenfassungen keine leere Überschrift
        parts.append(t("before_scenes") + "\n" + "\n".join(earlier))
    if people:
        parts.append(t("profiles_lower") + "\n" + "\n".join(
            f"- {e['name']}: {e.get('description', '')} " + "; ".join(f"{f['key']}: {f['value']}" for f in e.get("fields", []))
            for e in people))
    parts.append(t("text_before", text=before) if before else t.unit["begins"])
    parts.append(t("selected", text=selection) if selection else t("continue_here"))
    if after:
        parts.append(t("text_after", text=after))
    return system, "\n\n".join(parts) + "\n\n" + t("task", task=t(action))


_LEAD_HEADING = re.compile(r"^\s*#{1,6}[^\n]*\n+")
_LEAD_LABEL = re.compile(r"^\s*(?:\*\*)?(?:hier ist|here is|gekürzte|überarbeitete|ausgebaute|neue|fortsetzung|vorschlag|"
                         r"rewritten|shortened|expanded|continuation|revised)[^\n]{0,80}:(?:\*\*)?\s*\n+", re.IGNORECASE)


def clean_proposal(raw: str) -> str:
    """Denkblöcke und typischen Vorspann entfernen (Überschrift „# Gekürzte Fassung“, „Hier ist …:“).
    Der Vorschlag wird 1:1 in die Szene eingesetzt – so etwas darf dort nicht landen."""
    text = strip_think(raw).strip()   # auch nicht geschlossene Denkblöcke (Abbruch bei max_tokens)
    for _ in range(2):
        text = _LEAD_LABEL.sub("", _LEAD_HEADING.sub("", text, count=1), count=1).strip()
    if len(text) > 1 and text[0] == text[-1] and text[0] in "\"'":
        text = text[1:-1].strip()
    return text


async def suggest(user: str, project_id: str, book_id: str, scene_id: str, action: str,
                  selection: str, model: str | None, occurrence: int | None = None) -> dict:
    key = acquire(user, book_id)   # Sperre zuerst – sonst käme eine zweite Anfrage während des Lesens durch
    try:
        # Dateien lesen im Hilfs-Thread (A4) – die Ereignisschleife bedient derweil andere Anfragen. Fehler beim
        # Lesen (Szene/Buch weg) gehen unverändert weiter (404 usw.), nur Modellfehler werden zu llm_failed.
        system, prompt = await asyncio.to_thread(_context, project_id, book_id, scene_id, selection, action, occurrence)
        use_model = model or (await asyncio.to_thread(storage.get_book, project_id, book_id)).get("model") or None
        messages = [{"role": "system", "content": system},
                    {"role": "user", "content": prompt}]
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
