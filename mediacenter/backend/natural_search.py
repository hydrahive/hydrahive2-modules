"""Verbindet den Query-Parser mit der bestehenden Suchanfrage.

Laeuft serverseitig in der /search-Route: damit profitieren Oberflaeche UND
Agenten davon, ohne die Logik doppelt zu pflegen.

Zwei Regeln:
1. Explizite Angaben des Aufrufers gewinnen immer — der Parser ERGAENZT nur,
   was nicht gesetzt ist. Sonst wuerde Magie eine bewusste Eingabe ueberschreiben.
2. Der Medientyp des Aufrufers bleibt unangetastet (er ist Pflichtfeld und
   steuert Kategorien und Profilregeln).
"""
from __future__ import annotations

from .models import SearchRequest
from .query_parser import ParsedQuery, parse_query

# Welcher erkannte Filter ist fuer welchen Medientyp ueberhaupt erlaubt?
# Spiegelt die Validierung in SearchRequest — ein unpassender Filter wuerde
# dort eine Ausnahme ausloesen.
_ALLOWED_BY_MEDIA: dict[str, frozenset[str]] = {
    "season": frozenset({"tv"}),
    "episode": frozenset({"tv"}),
}


def apply_natural_language(request: SearchRequest) -> tuple[SearchRequest, ParsedQuery]:
    """Reichert die Anfrage um erkannte Filter an.

    Gibt (angereicherte Anfrage, Parser-Ergebnis) zurueck. Das Parser-Ergebnis
    wandert in die Antwort, damit die Oberflaeche zeigen kann, was verstanden
    wurde.
    """
    parsed = parse_query(request.query)
    if not parsed.recognized and parsed.query == request.query:
        return request, parsed

    updates: dict[str, object] = {}
    # Bereinigter Suchbegriff — aber nie kuerzer als die Modell-Mindestlaenge.
    if len(parsed.query) >= 2:
        updates["query"] = parsed.query

    if request.year is None and parsed.year is not None:
        updates["year"] = parsed.year

    for field, value in (("season", parsed.season), ("episode", parsed.episode)):
        if value is None or getattr(request, field) is not None:
            continue
        if request.media_type not in _ALLOWED_BY_MEDIA[field]:
            continue
        updates[field] = str(value) if field == "episode" else value

    if not updates:
        return request, parsed
    return request.model_copy(update=updates), parsed
