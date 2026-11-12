"""Liste der Bausteine eines Boards: Art, Gruppe und Name.

Eine Quelle für den Board-Text (render.py), die Prüfung von Vorschlägen und die
automatische Anordnung. Die Oberfläche führt dieselbe Liste in
frontend/palette-data.ts; tests/test_catalog.py hält beide in Deckung.
"""
from __future__ import annotations

from typing import NamedTuple


class Subtype(NamedTuple):
    kind: str
    name: str


# Reihenfolge = Reihenfolge der Abschnitte im Board-Text.
KINDS = ("layout", "flow", "build")
KIND_TITLES = {"layout": "Layout", "flow": "Ablauf", "build": "Aufbau"}
DEFAULT_KIND = "flow"

SUBTYPES: dict[str, Subtype] = {
    # Layout: wie eine Seite aussehen soll
    "page": Subtype("layout", "Seite"),
    "card": Subtype("layout", "Karte / Box"),
    "menu_item": Subtype("layout", "Menü-Eintrag"),
    "button": Subtype("layout", "Button"),
    "input": Subtype("layout", "Eingabefeld"),
    "toggle": Subtype("layout", "Schalter"),
    "heading": Subtype("layout", "Überschrift"),
    "list": Subtype("layout", "Liste / Tabelle"),
    # Ablauf: was passiert
    "event": Subtype("flow", "Event"),
    "action": Subtype("flow", "Aktion"),
    "datasource": Subtype("flow", "Datenquelle"),
    "condition": Subtype("flow", "Bedingung"),
    "display": Subtype("flow", "Anzeige"),
    "note": Subtype("flow", "Notiz"),
    # Aufbau: wie man es bauen könnte
    "module": Subtype("build", "Modul"),
    "interface": Subtype("build", "Schnittstelle"),
    "database": Subtype("build", "Datenbank / Tabelle"),
    "file": Subtype("build", "Datei"),
    "agent_tool": Subtype("build", "Agent-Werkzeug"),
}

# Bausteine mit einem Platzhalter-Feld (hasPlaceholder in frontend/palette-data.ts).
WITH_PLACEHOLDER = frozenset({"input"})


def kind_of(value: object) -> str:
    """Gruppe eines Bausteins. Unbekannte und fehlende Angaben zählen zum Ablauf."""
    return value if value in KINDS else DEFAULT_KIND
