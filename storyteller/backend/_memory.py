"""Gedächtnis eines Buchs für das Ghostwriter-Material (A4, Spec leistung-a4.md §2.1).

Kopf, Gliederung und die Infos (Titel, Zusammenfassung, Wörter) aller Szenen einmal lesen – ohne Szenentexte. Texte nur
bei Bedarf: die Szene selbst und das Ende der vorigen. So bleibt die Schätzung eines Laufs linear statt quadratisch.
"""
from __future__ import annotations

from . import storage

PREV_END = 1500         # so viel vom Ende der vorigen Szene, für den nahtlosen Anschluss


def fit_lines(lines: list[str], limit: int) -> str:
    """Die jüngsten Zeilen, die zusammen in ``limit`` Zeichen passen – nie eine halbe Zeile (A5a2). Passt nicht einmal
    die letzte, wird sie von vorn gekürzt und beginnt mit „…“ (sonst wäre das Gedächtnis leer)."""
    kept, size = [], -1
    for line in reversed(lines):
        if size + 1 + len(line) > limit:
            break
        kept.append(line)
        size += 1 + len(line)
    if not kept and lines and limit > 1:
        return "…" + lines[-1][-(limit - 1):]
    return "\n".join(reversed(kept))


def _size(blocks: list[list[str]]) -> int:
    return len("\n".join(line for b in blocks for line in b))


class MemoryIndex:
    """Gedächtnis eines Buchs für viele Szenen (A4): Kopf, Gliederung und die Infos (Titel, Zusammenfassung) aller
    Szenen einmal lesen – ohne Szenentexte. ``refresh(scene_id)`` zieht eine geänderte Szene nach (im Lauf nach jeder
    geschriebenen Szene). Texte werden nur bei Bedarf gelesen (die Szene selbst, das Ende der vorigen)."""

    def __init__(self, project_id: str, book_id: str, book: dict, structure: dict, infos: dict[str, dict],
                 chapter_summaries: dict[str, str] | None = None):
        self.project_id, self.book_id, self.book, self.structure, self.infos = project_id, book_id, book, structure, infos
        self.chapters = [c for p in structure["parts"] for c in p["chapters"]]
        self.order = [s for c in self.chapters for s in c["scenes"]]
        self.chapter_summaries = chapter_summaries or {}

    @classmethod
    def load(cls, project_id: str, book_id: str) -> MemoryIndex:
        from .chapter_summaries import from_structure
        st = storage.get_structure(project_id, book_id)
        order = [s for p in st["parts"] for c in p["chapters"] for s in c["scenes"]]
        return cls(project_id, book_id, storage.get_book(project_id, book_id), st,
                   {s: storage.scene_info(project_id, book_id, s) for s in order},
                   from_structure(project_id, book_id, st))

    def refresh(self, scene_id: str) -> None:
        self.infos[scene_id] = storage.scene_info(self.project_id, self.book_id, scene_id)

    def memory(self, scene_id: str, memory_chars: int) -> str:
        """Was bisher geschah (A5c, ohne feste Kapitelzahl – Till 10.10.): jedes frühere Kapitel Szene für Szene, solange
        alles in ``memory_chars`` passt. Sonst werden die ältesten Kapitel mit Kapitel-Zusammenfassung nacheinander zu
        einer Zeile, bis es passt – nur wenn das Platz spart. Das aktuelle Kapitel nie (seine Zusammenfassung kann
        Späteres verraten). Was dann noch zu lang ist, kürzt fit_lines an Zeilengrenzen."""
        from ._texts import texts
        t = texts(self.book)
        here = next(n for n, c in enumerate(self.chapters) if scene_id in c["scenes"])
        blocks: list[list[str]] = []           # je Kapitel bis zum aktuellen: seine Szenen-Zeilen
        for n, ch in enumerate(self.chapters[:here + 1]):
            scenes = ch["scenes"][:ch["scenes"].index(scene_id)] if n == here else ch["scenes"]
            blocks.append([f"- {i['title']}: {i['summary']}" for i in (self.infos[s] for s in scenes) if i["summary"].strip()])
        for n, ch in enumerate(self.chapters[:here]):
            summary = " ".join(self.chapter_summaries.get(ch["id"], "").split())
            if summary and not blocks[n]:       # Kapitel ohne Szenen-Zusammenfassungen: die Kapitel-Zeile ist alles, was es gibt
                blocks[n] = [t("chapter_line", title=ch["title"], summary=summary)]
        for n, ch in enumerate(self.chapters[:here]):
            if _size(blocks) <= memory_chars:
                break
            summary = " ".join(self.chapter_summaries.get(ch["id"], "").split())
            line = t("chapter_line", title=ch["title"], summary=summary) if summary else ""
            if line and len(line) < len("\n".join(blocks[n])):
                blocks[n] = [line]
        return fit_lines([line for b in blocks for line in b], memory_chars)

    def prev_end(self, scene_id: str) -> str:
        i = self.order.index(scene_id)
        if not i:
            return ""
        return storage.get_scene(self.project_id, self.book_id, self.order[i - 1])["text"][-PREV_END:]
