"""Werkzeuge für Agenten (Spec §6, §12.5): diagramm_erstellen, diagramm_hilfe, diagramm_liste. Kein Lösch-Werkzeug."""
from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path

from hydrahive.tools.base import Tool, ToolContext, ToolResult

from . import chains, help_text, preview, runner, store
from .errors import KNOWN

TITLE_FALLBACK = "Diagramm"
_FRONT_TITLE = re.compile(r"^---\s*\n(?:.*\n)*?title:\s*(.+?)\s*\n(?:.*\n)*?---", re.MULTILINE)
# Archify-Antwort-Seiten beginnen mit „# Titel {#id}“: nur die erste nichtleere Zeile zählt (sonst würde
# z. B. ein „# Kommentar“ in einem Codeblock weiter unten zum Titel). Der Anker gehört nicht dazu.
_H1_TITLE = re.compile(r"\A\s*#[ \t]+(.*?)[ \t]*(?:\{#[^}]*\})?[ \t]*$", re.MULTILINE)


def _explainer_title(source: str) -> str:
    m = _FRONT_TITLE.match(source)
    if m and m.group(1).strip().strip("\"'"):
        return m.group(1).strip().strip("\"'")
    h1 = _H1_TITLE.match(source)
    return h1.group(1).strip() if h1 else ""


def _title(kind: str, source: str) -> str:
    if kind == "explainer":
        return _explainer_title(source)[:200] or TITLE_FALLBACK
    try:
        title = json.loads(source).get("meta", {}).get("title")
    except (ValueError, AttributeError):
        return TITLE_FALLBACK
    return title.strip()[:200] if isinstance(title, str) and title.strip() else TITLE_FALLBACK


def _force_output(kind: str, source: str) -> str:
    """meta.output fest auf unsere Datei – der Agent kann nicht woanders hinschreiben."""
    if kind == "explainer":
        return source
    try:
        data = json.loads(source)
    except ValueError:
        return source
    if isinstance(data, dict) and isinstance(data.get("meta"), dict):
        data["meta"]["output"] = runner.OUTPUT
        return json.dumps(data, ensure_ascii=False)
    return source


def _repo(ctx: ToolContext, requested: str | None) -> tuple[Path | None, str | None]:
    if not requested:
        return None, None
    from hydrahive.tools._path import PathOutsideWorkspace, safe_path
    try:
        path = safe_path(ctx.workspace, requested)
    except PathOutsideWorkspace:
        return None, KNOWN["diagram_repo_outside"]
    if not path.is_dir():
        return None, KNOWN["diagram_repo_outside"]
    return path, None


def _fail(code: str, detail: str = "") -> ToolResult:
    return ToolResult.fail(KNOWN.get(code, KNOWN["diagram_failed"]) + (f"\n{detail}" if detail else ""))


async def _create(args: dict, ctx: ToolContext) -> ToolResult:
    kind, source = args.get("art"), args.get("beschreibung")
    if not isinstance(kind, str) or not isinstance(source, str) or not source.strip():
        return ToolResult.fail("art und beschreibung angeben (siehe diagramm_hilfe).")
    previous = args.get("ersetzt")
    if previous and not store.can_view(store.get(previous), ctx.user_id, "user"):
        return _fail("diagram_not_found")
    repo, problem = _repo(ctx, args.get("repo"))
    if problem:
        return ToolResult.fail(problem)
    source = _force_output(kind, source)
    with tempfile.TemporaryDirectory(prefix="diagramm-") as tmp:
        res = runner.build(kind, source, work=Path(tmp), repo_root=repo)
    if not res.ok:
        return _fail(res.code, res.detail)
    title = _title(kind, source)
    saved = store.create(username=ctx.user_id, project_id=ctx.project_id, session_id=ctx.session_id,
                         agent_id=ctx.agent_id, title=title, kind=kind, html=res.html or "", source=source,
                         source_ext="md" if kind == "explainer" else "json", version_of=previous or None)
    preview.make(saved["id"])  # Vorschaubild für die Sammlung – nie Pflicht
    text = (f"Diagramm „{title}“ erstellt und gespeichert (ID {saved['id']}). Es erscheint im Chat und unter "
            f"Diagramme. Zum Ändern: diagramm_erstellen mit ersetzt=\"{saved['id']}\" – die alte Fassung bleibt.")
    return ToolResult.ok(text, result_type="module_view", module="diagramme", view_id=saved["id"], title=title)


async def _help(args: dict, ctx: ToolContext) -> ToolResult:
    kind = args.get("art")
    if not kind:
        return ToolResult.ok(help_text.overview())
    text = help_text.for_kind(kind)
    return ToolResult.ok(text) if text else ToolResult.fail(KNOWN["diagram_kind_unknown"])


LIST_LIMIT = 30


async def _list(args: dict, ctx: ToolContext) -> ToolResult:
    rows = chains.newest_per_chain(store.list_for(ctx.user_id, "user"))
    if args.get("projekt") is True:
        rows = [r for r in rows if r["project_id"] == ctx.project_id]
    needle = str(args.get("q") or "").strip().casefold()
    if needle:
        rows = [r for r in rows if needle in r["title"].casefold()]
    if not rows:
        return ToolResult.ok("Keine Diagramme gefunden.")
    lines = [f"- {r['id']} | {r['title']} | {r['kind']} | {r['created_at'][:16].replace('T', ' ')}"
             + (f" | {r['versions']} Fassungen" if r["versions"] > 1 else "") for r in rows[:LIST_LIMIT]]
    return ToolResult.ok("Diagramme (neueste zuerst; ändern mit diagramm_erstellen ersetzt=<ID>):\n" + "\n".join(lines))


diagramm_erstellen = Tool(
    name="diagramm_erstellen",
    description=(
        "Erstellt ein interaktives Diagramm (Ablauf, Aufbau, Datenbank, Zustände, Zeitleiste …) oder eine Antwort-Seite "
        "und speichert es dauerhaft. Es erscheint bedienbar im Chat. Vorher diagramm_hilfe für Schema und Beispiel "
        "der gewählten Art aufrufen. Bei Fehlern kommen die Hinweise von Archify zurück – damit nachbessern "
        "(höchstens 3 Versuche). Zum Ändern eines Diagramms ersetzt=<ID> angeben: neue Fassung, die alte bleibt."),
    schema={
        "type": "object", "required": ["art", "beschreibung"],
        "properties": {
            "art": {"type": "string", "enum": list(runner.KINDS)},
            "beschreibung": {"type": "string", "description": "Archify-JSON (bzw. Markdown bei explainer)."},
            "ersetzt": {"type": "string", "description": "ID eines vorhandenen Diagramms → neue Fassung davon."},
            "repo": {"type": "string", "description": "Ordner im Projekt für Code-Belege (optional)."},
        },
    },
    execute=_create,
    category="media",
)

diagramm_hilfe = Tool(
    name="diagramm_hilfe",
    description="Zeigt die Arten von Diagrammen oder für eine Art das Schema und ein Beispiel (vor diagramm_erstellen).",
    schema={"type": "object", "properties": {"art": {"type": "string", "enum": list(runner.KINDS)}}},
    execute=_help,
    category="media",
)

diagramm_liste = Tool(
    name="diagramm_liste",
    description="Zeigt die gespeicherten Diagramme (neueste Fassung, neueste zuerst) – zum Wiederfinden oder Ändern.",
    schema={"type": "object", "properties": {
        "q": {"type": "string", "description": "Titel enthält …"},
        "projekt": {"type": "boolean", "description": "true = nur Diagramme dieses Projekts"},
    }},
    execute=_list,
    category="media",
)

TOOLS = [diagramm_erstellen, diagramm_hilfe, diagramm_liste]
