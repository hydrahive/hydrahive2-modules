"""Hilfe für Agenten (Spec §6): Arten, Schema und Beispiel aus der mitgelieferten Archify-Kopie.

Beispiele sind Muster für den Aufbau, keine Inhalte zum Abschreiben (Archify SKILL.md, „Examples teach shape“).
"""
from __future__ import annotations

from pathlib import Path

from .runner import KINDS

VENDOR = Path(__file__).resolve().parents[1] / "vendor" / "archify"

# Art → (wofür, Beispieldatei); Archify SKILL.md „Type router“, auf Deutsch.
GUIDE: dict[str, tuple[str, str]] = {
    "architecture": ("Aufbau eines Systems: Teile, Dienste, Grenzen", "web-app.architecture.json"),
    "workflow": ("Ablauf mit Schritten, Entscheidungen, Spuren", "agent-tool-call.workflow.json"),
    "sequence": ("Wer ruft wen in welcher Reihenfolge (Anfrage/Antwort)", "cache-miss-request.sequence.json"),
    "dataflow": ("Wohin Daten fließen (Pipeline, Herkunft)", "product-analytics.dataflow.json"),
    "lifecycle": ("Zustände und Übergänge (Status, Wiederholen, Ende)", "deployment-release.lifecycle.json"),
    "erd": ("Datenbank: Tabellen, Spalten, Schlüssel, Beziehungen", "orders.erd.json"),
    "class": ("Klassen und ihre Beziehungen", "payments.class.json"),
    "tree": ("Baum: Ordner, Gliederung, Zerlegung", "payment-platform.tree.json"),
    "timeline": ("Was wann passiert ist (Zeitleiste)", "payment-incident.timeline.json"),
    "waterfall": ("Wo die Zeit hinging (Dauer, Überlappung)", "checkout-request.waterfall.json"),
    "explainer": ("Antwort-Seite: Ergebnis zuerst, dann Abschnitte", ""),
}
RULES = """Regeln:
- Eine Art wählen, Schema lesen, eigene IDs und Texte (Beispiel nur als Muster).
- Inhalte auf Deutsch, meta.locale "en" lassen (Bedienleiste), meta.quality_profile "showcase".
- meta.output setzt das Werkzeug selbst.
- Fehler von Archify genau lesen und gezielt nachbessern, höchstens 3 Versuche.
- Ändern: diagramm_erstellen mit ersetzt=<ID> (alte Fassung bleibt)."""


def overview() -> str:
    lines = [f"- {kind}: {GUIDE[kind][0]}" for kind in KINDS]
    return "Arten von Diagrammen:\n" + "\n".join(lines) + "\n\nDann diagramm_hilfe mit art=<Art> aufrufen.\n\n" + RULES


def _read(rel: str) -> str:
    path = VENDOR / rel
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def for_kind(kind: object) -> str | None:
    if kind not in GUIDE:
        return None
    purpose, example = GUIDE[kind]  # type: ignore[index]
    if kind == "explainer":
        return (f"Art explainer – {purpose}.\n\nAnleitung (Archify):\n{_read('references/explainer-authoring.md')}"
                f"\n\n{RULES}")
    parts = [f"Art {kind} – {purpose}.", RULES,
             f"Schema ({kind}):\n{_read(f'schemas/{kind}.schema.json')}",
             f"Gemeinsame Teile (common):\n{_read('schemas/common.schema.json')}",
             f"Beispiel ({example}):\n{_read(f'examples/{example}')}",
             f"Hinweise (Archify):\n{_read('references/authoring-defaults.md')}"]
    return "\n\n".join(parts)
