"""Ghostwriter G3 – Fragen vorschlagen und Interview als Material für den Szenen-Schreiber (Spec §10.1).

Fragen kommen als JSON; schon gestellte Fragen (dieses Kapitel) und beantwortete Fragen anderer Kapitel
gehen mit, damit nichts doppelt gefragt wird. Fürs Schreiben: alle Antworten des Kapitels + eine
Stilprobe (die längsten Antworten wörtlich, begrenzt) + die Regel, nichts darüber hinaus zu erfinden.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from hydrahive.llm.client import complete

from . import interviews, storage
from ._files import StoryError
from ._ghost_settings import ghost_of
from ._names import KIND_LABEL, LANGUAGE_LABEL

STYLE_SAMPLE = 1500     # Zeichen Originalwortlaut als Stilprobe
MAX_ANSWERS = 12000     # Zeichen aller Antworten im Material (die neuesten zuerst gekürzt)
_JSON = re.compile(r"(\{.*\}|\[.*\])", re.DOTALL)

RULE = ("Schreibe ausschließlich aus dem, was der Autor im Interview erzählt hat, und aus den Zusammenfassungen. "
        "Erfinde nichts dazu: keine Namen, Orte, Jahreszahlen oder Ereignisse, die dort nicht stehen – eine Lücke "
        "bleibt eine Lücke. Schreibe in der Stimme des Autors (Wortwahl, Satzlänge, Ich-Form, wenn er so erzählt).")


@dataclass(frozen=True)
class InterviewMaterial:
    answers: str          # „F: … / A: …“ je beantworteter Frage
    style_sample: str     # längste Antworten wörtlich

    @property
    def empty(self) -> bool:
        return not self.answers.strip()


def interview_material(project_id: str, book_id: str, chapter_id: str) -> InterviewMaterial:
    qs = [q for q in interviews.get(project_id, book_id, chapter_id)["questions"] if q["answer"].strip()]
    answers = "\n\n".join(f"F: {q['question']}\nA: {q['answer'].strip()}" for q in qs)[:MAX_ANSWERS]
    sample = ""
    for q in sorted(qs, key=lambda x: len(x["answer"]), reverse=True):
        if len(sample) >= STYLE_SAMPLE:
            break
        sample += ("\n…\n" if sample else "") + q["answer"].strip()[: STYLE_SAMPLE - len(sample)]
    return InterviewMaterial(answers, sample[:STYLE_SAMPLE])


def material_parts(iv: InterviewMaterial) -> list[str]:
    """Zusätzliche Abschnitte für den Prompt des Szenen-Schreibers."""
    return [f"INTERVIEW MIT DEM AUTOR (Grundlage des Textes):\n{iv.answers}",
            f"STIMME DES AUTORS (Originalwortlaut, so klingt er):\n{iv.style_sample}"]


def _parse(raw: str) -> list[str]:
    m = _JSON.search(re.sub(r"<think>.*?</think>", "", raw or "", flags=re.DOTALL))
    if not m:
        raise ValueError("kein JSON")
    data: Any = json.loads(m.group(0))
    items = data.get("questions") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise ValueError("keine Liste")
    out = [q.strip() for q in items if isinstance(q, str) and q.strip() and len(q.strip()) <= interviews.MAX_QUESTION]
    if not out:
        raise ValueError("leer")
    return out


async def suggest_questions(project_id: str, book_id: str, chapter_id: str, *, count: int) -> list[str]:
    if not 1 <= count <= 8:
        raise StoryError("questions_count_invalid")
    book = storage.get_book(project_id, book_id)
    st = storage.get_structure(project_id, book_id)
    ch = next((c for p in st["parts"] for c in p["chapters"] if c["id"] == chapter_id), None)
    if ch is None:
        raise StoryError("chapter_not_found", 404)
    summaries = [storage.get_scene(project_id, book_id, s) for s in ch["scenes"]]
    asked = [q["question"] for q in interviews.get(project_id, book_id, chapter_id)["questions"]]
    elsewhere = interviews.answered_elsewhere(project_id, book_id, chapter_id)
    lang = LANGUAGE_LABEL.get(book["language"], book["language"])
    system = (f"Du bist Ghostwriter und interviewst den Autor eines Buchs ({KIND_LABEL.get(book['kind'], book['kind'])}) "
              f"auf {lang}. Stelle offene, konkrete Fragen, die Erinnerungen, Erlebnisse, Fakten und Gefühle "
              'hervorlocken – je eine Sache pro Frage. Antworte NUR mit JSON: {"questions": ["…", "…"]}.')
    prompt = "\n".join(p for p in [
        f"BUCH: {book['title']}. Idee: {book.get('idea') or '–'}. Zielgruppe: {book.get('audience') or '–'}",
        f"KAPITEL: {ch['title']}",
        "INHALT DES KAPITELS:\n" + "\n".join(f"- {s['title']}: {s['summary']}" for s in summaries if s["summary"].strip()),
        ("SCHON GESTELLT (nicht wiederholen):\n" + "\n".join(f"- {q}" for q in asked)) if asked else "",
        ("AUS ANDEREN KAPITELN SCHON BEKANNT:\n" + "\n".join(f"- {e['question']} → {e['answer'][:200]}" for e in elsewhere[:20]))
        if elsewhere else "",
        f"\nAUFGABE: {count} neue Fragen zu diesem Kapitel.",
    ] if p)
    model = ghost_of(book)["model"] or book.get("model") or None
    messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
    raw = await complete(messages, model=model, temperature=0.7, max_tokens=1500)
    for attempt in range(2):
        try:
            return _parse(raw)[:count]
        except (ValueError, json.JSONDecodeError):
            if attempt:
                raise StoryError("questions_invalid", 502) from None
            messages += [{"role": "assistant", "content": raw or ""},
                         {"role": "user", "content": 'Bitte nur das JSON: {"questions": ["…"]}'}]
            raw = await complete(messages, model=model, temperature=0.3, max_tokens=1500)
    raise StoryError("questions_invalid", 502)   # nicht erreichbar
