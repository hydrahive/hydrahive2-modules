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


class MemoryIndex:
    """Gedächtnis eines Buchs für viele Szenen (A4): Kopf, Gliederung und die Infos (Titel, Zusammenfassung) aller
    Szenen einmal lesen – ohne Szenentexte. ``refresh(scene_id)`` zieht eine geänderte Szene nach (im Lauf nach jeder
    geschriebenen Szene). Texte werden nur bei Bedarf gelesen (die Szene selbst, das Ende der vorigen)."""

    def __init__(self, project_id: str, book_id: str, book: dict, structure: dict, infos: dict[str, dict]):
        self.project_id, self.book_id, self.book, self.structure, self.infos = project_id, book_id, book, structure, infos
        self.order = [s for p in structure["parts"] for c in p["chapters"] for s in c["scenes"]]

    @classmethod
    def load(cls, project_id: str, book_id: str) -> MemoryIndex:
        st = storage.get_structure(project_id, book_id)
        order = [s for p in st["parts"] for c in p["chapters"] for s in c["scenes"]]
        return cls(project_id, book_id, storage.get_book(project_id, book_id), st,
                   {s: storage.scene_info(project_id, book_id, s) for s in order})

    def refresh(self, scene_id: str) -> None:
        self.infos[scene_id] = storage.scene_info(self.project_id, self.book_id, scene_id)

    def memory(self, scene_id: str, memory_chars: int) -> str:
        earlier = self.order[:self.order.index(scene_id)]
        lines = [f"- {i['title']}: {i['summary']}" for i in (self.infos[s] for s in earlier) if i["summary"].strip()]
        return fit_lines(lines, memory_chars)

    def prev_end(self, scene_id: str) -> str:
        i = self.order.index(scene_id)
        if not i:
            return ""
        return storage.get_scene(self.project_id, self.book_id, self.order[i - 1])["text"][-PREV_END:]
