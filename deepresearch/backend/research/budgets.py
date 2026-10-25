"""Antwortgrenzen (Token) je Schritt – an einer Stelle (SPEC.md).

Deep Research soll ausführlich schreiben (Till, 25.10.2026). Bezahlt wird, was
das Modell schreibt, nicht die Grenze – hohe Grenzen schneiden nur nicht mehr ab.
Vorher war die Auswertung je Seite auf 700 begrenzt: lange Antworten brachen
mitten im JSON ab und die Seite wurde still verworfen.

REPORT läuft über Streaming: Das Anthropic-SDK lehnt Antworten ohne Streaming
oberhalb von ~21.000 Token ab (10-Minuten-Grenze).
"""
from __future__ import annotations

PLAN = 4_000          # Teilfragen + Kategorie (JSON)
QUERIES = 2_000       # Suchbegriffe einer Runde (JSON)
EXTRACT = 8_000       # gründliche Auswertung je Seite (JSON)
SYNTHESIZE = 16_000   # laufender Arbeitsbericht
REPORT = 32_000       # finaler Bericht (Streaming)
STOP = 50             # nur YES/NO

MAX_TIME_S = 900.0    # ausführliches Schreiben braucht länger als die alten 300 s
