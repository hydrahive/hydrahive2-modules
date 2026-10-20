"""Fehlercodes des Moduls Diagramme mit kurzem Text (für Agenten und Oberfläche)."""
from __future__ import annotations

KNOWN: dict[str, str] = {
    "diagram_not_found": "Diagramm nicht gefunden.",
    "diagram_kind_unknown": "Diese Art von Diagramm gibt es nicht.",
    "diagram_input_too_large": "Die Beschreibung ist zu groß.",
    "diagram_invalid": "Die Beschreibung passt nicht – Archify meldet Fehler.",
    "diagram_timeout": "Das Erstellen hat zu lange gedauert.",
    "diagram_node_missing": "Node fehlt auf dem Server – Diagramme können nicht erstellt werden.",
    "diagram_failed": "Das Diagramm konnte nicht erstellt werden.",
    "diagram_repo_outside": "Der Ordner liegt nicht im Projekt.",
}
