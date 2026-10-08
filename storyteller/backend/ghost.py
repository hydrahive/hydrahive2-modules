"""Ghostwriter G1 (Spec ghostwriter.md §3/§5): Material sammeln und eine Szene in Abschnitten schreiben.

Ändert nichts am Buch – liefert nur Text (als Generator, damit die Oberfläche live mitlesen und
abbrechen kann). Kein festes Modell im Code: Anfrage → Ghostwriter-Modell des Buchs → Buchmodell →
HydraHive-Standard (``None``).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import AsyncIterator

from hydrahive.llm.client import complete, stream

from . import storage
from ._files import StoryError
from ._ghost_settings import ghost_of
from ._names import KIND_LABEL, LANGUAGE_LABEL
from ._think import ThinkFilter
from ._memory import PREV_END, MemoryIndex
from .ai import clean_proposal

MAX_SECTIONS = 4
REACHED = 0.85          # Länge gilt als erreicht ab 85 % des Ziels
_PREV_END = PREV_END     # so viel vom Ende der vorigen Szene (eine Stelle: _memory.PREV_END)
_SO_FAR = 3000          # so viel vom bereits Geschriebenen bei Folgeabschnitten
_MEMORY = 4000          # Gedächtnis: höchstens so viele Zeichen Zusammenfassungen (die jüngsten)
_HEAD_BUFFER = 400      # Anfang eines Abschnitts so lange zurückhalten (Überschrift/Vorspann erkennen)
_OUTLINE_HEAD = 400     # je früherem Abschnitt so viel vom Anfang als Übersicht (gegen Wiederholungen)


@dataclass(frozen=True)
class Material:
    scene_id: str
    mode: str           # "fill" = leere Szene, "proposal" = Szene hat schon Text
    system: str
    prompt: str


def choose_model(book: dict, requested: str | None) -> str | None:
    return requested or ghost_of(book)["model"] or book.get("model") or None


def plan_lengths(book: dict, requested_words: int | None) -> tuple[int, int]:
    """(Ziel-Wörter, Abschnitt-Wörter) aus Anfrage bzw. Buch-Einstellungen – keine eingebauten Werte."""
    g = ghost_of(book)
    length = requested_words or g["length_words"]
    if not length:
        raise StoryError("length_required")
    chunk = g["chunk_words"] or length
    return length, min(chunk, length)


def _names_in(text: str, entities: list[dict]) -> list[dict]:
    low = text.lower()
    return [e for e in entities if any(
        n and re.search(rf"(?<!\w){re.escape(n.lower())}(?!\w)", low) for n in [e["name"], *e.get("aliases", [])])]


def build_material(project_id: str, book_id: str, scene_id: str, memory_chars: int = _MEMORY,
                   interview=None, index: MemoryIndex | None = None) -> Material:
    """``interview`` (G3, interview_ai.InterviewMaterial): Antworten des Autors + Stilprobe als Grundlage; dann
    darf die Zusammenfassung fehlen, und es gilt die Regel „nichts erfinden“.
    ``index`` (A4): für viele Szenen hintereinander einmal laden (Schätzung, Lauf) – sonst wird er hier gebaut."""
    from .interview_ai import RULE, material_parts
    idx = index or MemoryIndex.load(project_id, book_id)
    book, st = idx.book, idx.structure
    scene = storage.get_scene(project_id, book_id, scene_id)
    use_iv = interview is not None and not interview.empty
    if not scene["summary"].strip() and not use_iv:
        raise StoryError("summary_required")
    memory = idx.memory(scene_id, memory_chars)
    prev_end = idx.prev_end(scene_id)
    lang = LANGUAGE_LABEL.get(book["language"], book["language"])
    style = ghost_of(book)["style"]
    relevant = _names_in(" ".join([memory, scene["summary"], scene["pov"], scene["title"], prev_end]), st.get("entities", []))
    system = (
        f"Du bist Ghostwriter für ein Buch ({KIND_LABEL.get(book['kind'], book['kind'])}). Du schreibst Romantext "
        f"auf {lang} für genau EINE Szene. Keine Überschrift, kein Vorspann, keine Erklärung, keine Zusammenfassung "
        "am Ende – nur der Szenentext. Halte dich an Steckbriefe und bisherige Handlung und erfinde nichts, was "
        "ihnen widerspricht. Formuliere eigenständig; bekannte Texte anderer Autoren nicht zitieren oder nachschreiben."
        + (" " + RULE if use_iv else "")
    )
    parts = [
        f"BUCH: {book['title']}. Zielgruppe: {book.get('audience') or 'nicht angegeben'}. Idee: {book.get('idea') or '–'}",
        f"STIL: {style}" if style.strip() else "",
        "STECKBRIEFE:\n" + "\n".join(
            f"- {e['name']}: {e.get('description', '')} " + "; ".join(f"{f['key']}: {f['value']}" for f in e.get("fields", []))
            for e in relevant) if relevant else "",
        f"BISHER GESCHAH:\n{memory}" if memory else "Dies ist die erste Szene des Buchs.",
        f"ENDE DER VORIGEN SZENE (wörtlich, schließe nahtlos an):\n…{prev_end}" if prev_end.strip() else "",
        *(material_parts(interview) if use_iv else []),
        f"DIESE SZENE: „{scene['title']}“. Inhalt: {scene['summary'] or 'aus dem Interview (passender Teil)'}"
        + (f" Perspektive: {scene['pov']}." if scene["pov"].strip() else ""),
    ]
    return Material(scene_id, "proposal" if scene["text"].strip() else "fill", system, "\n\n".join(p for p in parts if p))


def _trailing_ws(text: str) -> str:
    """clean_proposal schneidet Leerraum am Ende ab; beim Streamen muss der Abstand zum nächsten Stück bleiben."""
    return text[len(text.rstrip()):]


async def write_scene(material: Material, *, model: str | None, length_words: int, chunk_words: int) -> AsyncIterator[str]:
    """Schreibt Abschnitt für Abschnitt, bis die Länge ungefähr erreicht ist (max. MAX_SECTIONS).
    Liefert Textstücke; Überschrift/Vorspann je Abschnitt entfernt. Schließen des Generators bricht ab."""
    written = ""
    starts: list[str] = []   # Anfang jedes geschriebenen Abschnitts – Übersicht für spätere Abschnitte
    for section in range(MAX_SECTIONS):
        left = length_words - len(written.split())
        if left <= length_words * (1 - REACHED):
            return
        target = min(chunk_words, max(left, 150))
        task = (f"Schreibe den {'Anfang' if section == 0 else 'nächsten Abschnitt'} dieser Szene, etwa {target} Wörter."
                + (" Setze genau dort fort, wo der Text aufhört. Nichts wiederholen: keine Gespräche, Fragen oder "
                   "Ereignisse, die oben schon vorkommen – die Handlung geht weiter." if written else ""))
        overview = ("\n\nBISHERIGE ABSCHNITTE DIESER SZENE (jeweils der Anfang):\n"
                    + "\n".join(f"{i + 1}. {h}…" for i, h in enumerate(starts))) if len(starts) > 1 else ""
        so_far = f"{overview}\n\nSO WEIT GESCHRIEBEN (Ende):\n…{written[-_SO_FAR:]}" if written else ""
        messages = [{"role": "system", "content": material.system},
                    {"role": "user", "content": f"{material.prompt}{so_far}\n\nAUFGABE: {task}"}]
        head, sent = "", False   # Anfang puffern, bis Überschrift/Vorspann sicher erkannt ist
        think = ThinkFilter()    # Denktext (<think>…) nie durchreichen, auch wenn er länger als der Puffer ist
        llm = stream(messages, model=model, temperature=0.8, max_tokens=max(1024, target * 3))
        try:
            async for raw in llm:
                piece = think.feed(raw)
                if sent:
                    if piece:
                        written += piece
                        yield piece
                    continue
                head += piece
                if len(head) < _HEAD_BUFFER:
                    continue
                clean = clean_proposal(head)
                if clean:
                    out = ("\n\n" if written else "") + clean + _trailing_ws(head)
                    written += out
                    starts.append(" ".join(clean[:_OUTLINE_HEAD].split()))
                    sent = True
                    yield out
        finally:
            await llm.aclose()   # Abbruch durch den Nutzer: Verbindung zum Modell sofort schließen
        rest = think.end()
        if sent and rest:
            written += rest
            yield rest
        if not sent:                    # sehr kurze Antwort: alles war im Puffer
            clean = clean_proposal(head + rest)
            if not clean:
                return
            out = ("\n\n" if written else "") + clean
            written += out
            starts.append(" ".join(clean[:_OUTLINE_HEAD].split()))
            yield out


async def summarize_scene(project_id: str, book_id: str, scene_id: str) -> dict:
    """Gedächtnis nach dem Annehmen: 2–3 Sätze, nur wenn die Zusammenfassung leer ist."""
    book = storage.get_book(project_id, book_id)
    scene = storage.get_scene(project_id, book_id, scene_id)
    if scene["summary"].strip() or not scene["text"].strip():
        return {"kept": True, "scene": scene}
    lang = LANGUAGE_LABEL.get(book["language"], book["language"])
    raw = await complete([
        {"role": "system", "content": f"Fasse die Szene in 2–3 Sätzen auf {lang} zusammen: was passiert und welche "
                                      "Fakten über Figuren neu sind. Nur die Zusammenfassung, keine Überschrift."},
        {"role": "user", "content": scene["text"][-12000:]},
    ], model=choose_model(book, None), temperature=0.2, max_tokens=400)
    summary = clean_proposal(raw or "")[:2000]
    if not summary:
        raise StoryError("llm_empty", 502)
    saved = storage.save_scene(project_id, book_id, scene_id, {"summary": summary}, base_version=scene["version"])
    return {"kept": False, "scene": saved}
