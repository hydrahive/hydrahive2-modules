"""Agent-Werkzeuge legal_search / legal_norm (Plan L1 Schritt 7). Gesetze sind öffentlich → Stufe normal.

Die Beschreibung von legal_search folgt der L0-Messung (Spec §6a): Fachbegriffe 19/20 in den Top 5,
Laiensprache nur 13/20 in den Top 10 – der Agent soll vorher in Gesetzessprache übersetzen.
"""
from __future__ import annotations

from hydrahive.tools.base import Tool, ToolContext, ToolResult

from . import corpus_store, norm_view, search

_EMPTY = ("Im Recht-Modul sind noch keine Gesetze geladen. Ein Admin startet den Abgleich unter "
          "Recht → Gesetze (oder er läuft automatisch kurz nach dem Start).")

_SEARCH_DESC = (
    "Sucht Normen in den lokal gespeicherten Bundesgesetzen (BGB, ZPO, StGB, SGB, FamFG, WEG, BauGB u. a., amtlicher "
    "Text von gesetze-im-internet.de). Mit Fachbegriffen aus dem Gesetz suchen, nicht in Alltagssprache "
    "(„Mangel Mietsache Anzeige Mieter“ statt „Wohnung zu heiß melden“); zusammengesetzte Wörter getrennt "
    "(„Widerspruch Frist“ statt „Widerspruchsfrist“). Eine Normbezeichnung („§ 536c BGB“) trifft direkt. "
    "Bei wenig Treffern mit anderen Fachbegriffen erneut suchen. Danach den Wortlaut mit legal_norm holen – "
    "keine Rechtsaussage ohne gelesene Norm."
)

_SEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "Fachbegriffe oder Normbezeichnung."},
        "law": {"type": "string", "description": "Optional: nur in diesem Gesetz (Kürzel, z. B. BGB, VwGO)."},
        "limit": {"type": "integer", "minimum": 1, "maximum": search.MAX_LIMIT, "default": 10},
    },
    "required": ["query"],
}

_NORM_DESC = (
    "Holt den amtlichen Wortlaut einer Norm mit Stand und Link zu gesetze-im-internet.de, z. B. „§ 536c BGB“, "
    "„Art. 3 GG“, „§ 7 SGB II“. Mit as_of (JJJJ-MM-TT) die Fassung, die an diesem Tag galt, sofern sie lokal vorliegt. "
    "Zitiere Normen in Antworten und Briefen nur so, wie dieses Werkzeug sie liefert."
)

_NORM_SCHEMA = {
    "type": "object",
    "properties": {
        "citation": {"type": "string", "description": "Normbezeichnung, z. B. „§ 536c BGB“."},
        "as_of": {"type": "string", "description": "Optional: Datum JJJJ-MM-TT für eine frühere Fassung."},
    },
    "required": ["citation"],
}


async def _search(args: dict, ctx: ToolContext) -> ToolResult:
    if not corpus_store.known_abbrs():
        return ToolResult.fail(_EMPTY)
    try:
        hits = search.search(str(args.get("query", "")), law=args.get("law") or None,
                             limit=int(args.get("limit", 10)))
    except (search.SearchError, ValueError) as e:
        return ToolResult.fail(str(e))
    out: dict = {"hits": [{k: h[k] for k in ("abbr", "enbez", "heading", "snippet", "match")} for h in hits]}
    if not hits:
        out["hint"] = ("Keine Treffer. Mit anderen Fachbegriffen suchen, zusammengesetzte Wörter trennen oder das "
                       "Gesetz mit law eingrenzen.")
    return ToolResult.ok(out)


async def _norm(args: dict, ctx: ToolContext) -> ToolResult:
    if not corpus_store.known_abbrs():
        return ToolResult.fail(_EMPTY)
    try:
        return ToolResult.ok(norm_view.lookup(str(args.get("citation", "")), as_of=args.get("as_of") or None))
    except norm_view.NormError as e:
        return ToolResult.fail(str(e))


LEGAL_SEARCH = Tool(name="legal_search", description=_SEARCH_DESC, schema=_SEARCH_SCHEMA, execute=_search,
                    category="legal")
LEGAL_NORM = Tool(name="legal_norm", description=_NORM_DESC, schema=_NORM_SCHEMA, execute=_norm, category="legal")

from .case_tools import TOOLS as CASE_TOOLS

TOOLS = [LEGAL_SEARCH, LEGAL_NORM, *CASE_TOOLS]
