"""Storyteller — Werkzeuge für Agenten im HydraHive-Chat (Ghostwriter G4, Spec ghostwriter.md §11).

Grundsätze:
- Nur das **Projekt der Chat-Sitzung** (``ToolContext.project_id``) – kein frei wählbares Projekt.
- Rechte wie die Oberfläche: Projektrolle des Nutzers (``ToolContext.user_id``), System-Admin darf alles.
  Lesen: ``read``. Vorschläge: ``write``.
- Der Agent ändert das Buch nie direkt; Text landet als abgelegter Vorschlag (proposals.py).
Erweiterungen (Spec §11.5) kommen als weitere ``storyteller_propose_*``-Werkzeuge dazu (G4b: Szenen-Infos, G4c: Steckbriefe, G4d: Gliederung).
"""
from __future__ import annotations

from hydrahive.tools.base import ToolContext, ToolResult

from .._files import project_access

HINT = """
Storyteller (Bücher im Projekt): storyteller_books → storyteller_outline → storyteller_read, um Bücher zu lesen.
Neuen oder überarbeiteten Szenentext NIE mit Datei-Werkzeugen in storyteller/books schreiben, sondern
immer mit storyteller_propose_text: Das legt einen Vorschlag an der Szene ab, den der Autor im Storyteller
ansieht und übernimmt oder verwirft. Titel, Zusammenfassung oder Perspektive einer Szene schlägst du mit
storyteller_propose_scene_info vor, neue oder geänderte Steckbriefe (Figuren, Orte, Gegenstände) mit
storyteller_propose_entity, neue Kapitel mit Szenen (Gliederung) mit storyteller_propose_outline.
Befunde und Wissen (Widerspruch, Stilproblem, Recherche mit Quellen) legst du mit storyteller_note ab,
lesen mit storyteller_notes.
Vorher die Szene lesen; Steckbriefe und Zusammenfassungen beachten.
"""


def scope(ctx: ToolContext, need: str = "read") -> tuple[str | None, ToolResult | None]:
    """(project_id, None) wenn erlaubt, sonst (None, Fehler). ``need``: read | write."""
    pid = (ctx.project_id or "").strip()
    if not pid:
        return None, ToolResult.fail("Dieser Chat gehört zu keinem Projekt. Den Chat aus dem Projekt bzw. aus dem "
                                     "Storyteller starten, dann sind dessen Bücher erreichbar.")
    from hydrahive.api.middleware.users import get_by_username
    user = get_by_username(ctx.user_id or "") or {}
    result = project_access(ctx.user_id or "", user.get("role", "user"), pid, need)
    if result == "missing":
        return None, ToolResult.fail("Kein Zugriff auf die Bücher dieses Projekts.")
    if result == "read_only":
        return None, ToolResult.fail("Nur Leserechte in diesem Projekt – Vorschläge sind nicht erlaubt.")
    return pid, None


from .entity import PROPOSE_ENTITY
from .note import NOTE, NOTES
from .outline_tool import PROPOSE_OUTLINE
from .propose import PROPOSE_INFO, PROPOSE_TEXT
from .read import BOOKS, OUTLINE, READ

TOOLS = [BOOKS, OUTLINE, READ, PROPOSE_TEXT, PROPOSE_INFO, PROPOSE_ENTITY, PROPOSE_OUTLINE, NOTE, NOTES]
