"""Schreib-Team je Buch-Projekt (Spec schreib-team.md §3): Autor (Projekt-Agent) + 7 Helfer (Spezialisten).

Rollen, Werkzeuge und Anweisungen liegen im Modul und wandern mit seiner Version. Grundsätze:
- Keine Entwickler-Werkzeuge (Shell, Dateien, Git, Agenten anlegen) – das Team schreibt nur.
- Helfer ändern das Buch nie direkt, nur über Vorschläge (``storyteller_propose_*``), soweit ihre Rolle das braucht.
- Nur der Autor gibt Aufträge (``ask_agent``); der Kern lässt Projekt-Agenten ohnehin nur freigegebene Spezialisten
  beauftragen (``allowed_specialists``).
- Alle nutzen dasselbe Modell (Till 07.10.); das Modell steht nie hier, sondern kommt vom Buch bzw. HydraHive-Standard.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

TEAM_VERSION = 1
_PROMPTS = Path(__file__).resolve().parent / "prompts"

READ = ("storyteller_books", "storyteller_outline", "storyteller_read",
        "datamining_search", "datamining_semantic", "datamining_timeline", "read_memory", "search_memory")
PROPOSE_ALL = ("storyteller_propose_text", "storyteller_propose_scene_info", "storyteller_propose_entity",
               "storyteller_propose_outline")


@dataclass(frozen=True)
class Role:
    key: str
    name: str
    description: str
    tools: tuple[str, ...]


AUTHOR = Role("author", "Autor", "Schreibt mit dir am Buch, plant und beauftragt die Helfer.",
              READ + PROPOSE_ALL + ("write_memory", "todo_write", "ask_agent", "list_specialists"))

HELPERS: tuple[Role, ...] = (
    Role("plausibility", "Plausibilität", "Findet Widersprüche zu Steckbriefen, Zeitlinie und Wissen der Figuren.",
         READ),
    Role("research", "Recherche", "Klärt Sachfragen und historische oder fachliche Details, mit Quellen.",
         READ + ("web_search", "fetch_url", "research_report")),
    Role("editor", "Lektor", "Prüft Stil, Wiederholungen, Lesbarkeit und KI-Floskeln; schlägt Überarbeitungen vor.",
         READ + ("storyteller_propose_text",)),
    Role("critic", "Kritiker", "Sucht Lücken in Handlung und Logik und schwache Spannung.", READ),
    Role("creative", "Kreativ", "Bringt Wendungen, Alternativen und neue Ideen ein.",
         READ + ("storyteller_propose_outline",)),
    Role("structure", "Struktur", "Achtet auf Aufbau, Akte, Spannungsbogen und Tempo.",
         READ + ("storyteller_propose_outline", "storyteller_propose_scene_info")),
    Role("profiles", "Steckbrief-Pfleger", "Übernimmt neue Fakten über Figuren, Orte und Gegenstände in Steckbriefe.",
         READ + ("storyteller_propose_entity",)),
)


def available_tools(role: Role, installed: Iterable[str]) -> list[str]:
    """Werkzeuge der Rolle, die es auf diesem Server gibt (z. B. research_report nur mit Deep-Research-Modul)."""
    have = set(installed)
    return [t for t in role.tools if t in have]


def _team_list(ids: Mapping[str, str] | None) -> str:
    lines = []
    for h in HELPERS:
        ident = f" (agent_id {ids[h.key]})" if ids and ids.get(h.key) else ""
        lines.append(f"- **{h.name}**{ident}: {h.description}")
    return "\n".join(lines)


def prompt_for(role: Role, *, book_title: str, team_ids: Mapping[str, str] | None = None) -> str:
    """Anweisung der Rolle mit Grundregeln. Der Titel wird zuletzt eingesetzt (kein Platzhalter im Titel wirkt)."""
    text = (_PROMPTS / f"{role.key}.md").read_text(encoding="utf-8").strip()
    common = (_PROMPTS / "_common.md").read_text(encoding="utf-8").strip()
    out = f"{text}\n\n{common}".replace("{team}", _team_list(team_ids))
    return out.replace("{book_title}", book_title)
