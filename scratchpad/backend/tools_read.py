"""Lese-Werkzeuge für Agenten: idea_list, idea_read und der Alias read_scratchpad."""
from __future__ import annotations

import json
from typing import Any

from hydrahive.tools.base import Tool, ToolContext, ToolResult

from . import access, legacy_import, notes, render, store
from ._ids import resolve

_DEFAULT_LIMIT = 20
_MAX_LIMIT = 100
_OUTPUT_BUDGET_CHARS = 40_000
_ALL_PROJECTS = "*"
_STATUS_CHOICES = ["open", "all", *store.STATUSES]

_LIST_SCHEMA = {
    "type": "object",
    "properties": {
        "project_id": {
            "type": "string",
            "description": "Projekt-ID. Ohne Angabe: das aktive Projekt des Laufs. "
                           "'*' = alle Projekte, 'none' = nur Ideen ohne Projekt.",
        },
        "status": {
            "type": "string", "enum": _STATUS_CHOICES, "default": "open",
            "description": "open (Standard: Neu, Wird geprüft, Geplant), all oder ein einzelner Status.",
        },
        "limit": {"type": "integer", "minimum": 1, "maximum": _MAX_LIMIT, "default": _DEFAULT_LIMIT,
                  "description": "Ideen dieser Seite (1–100, Standard 20)."},
        "offset": {"type": "integer", "minimum": 0, "default": 0,
                   "description": "Anzahl zu überspringender Ideen (Standard 0)."},
    },
}
_READ_SCHEMA = {
    "type": "object",
    "properties": {
        "idea_id": {"type": "string", "description": "ID der Idee (vollständig oder die ersten 8 Zeichen)."},
    },
    "required": ["idea_id"],
}
_HINT = (
    "\n\nIdeen: Der Nutzer hält Ideen einzeln fest (Kopfzeile, Beschreibung, Projekt, Status). "
    "Lies sie mit `idea_list` und `idea_read`, wenn er darauf verweist. Den Text des Nutzers "
    "änderst du nie: Anmerkungen und Statuswechsel gehen über `idea_write`."
)


def _page_args(args: dict) -> tuple[int, int] | None:
    limit, offset = args.get("limit", _DEFAULT_LIMIT), args.get("offset", 0)
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= _MAX_LIMIT:
        return None
    if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
        return None
    return limit, offset


def _statuses(value: Any) -> tuple[bool, tuple[str, ...] | None]:
    """(gültig, Statusfilter). ``None`` als Filter heißt alle."""
    wanted = str(value or "open").strip()
    if wanted == "all":
        return True, None
    if wanted == "open":
        return True, store.OPEN_STATUSES
    return (True, (wanted,)) if wanted in store.STATUSES else (False, None)


def _project_filter(args: dict, ctx: ToolContext) -> str | None:
    wanted = str(args.get("project_id") or "").strip()
    if wanted == _ALL_PROJECTS:
        return None
    return wanted or ctx.project_id or None


def _compact(idea: dict, names: dict[str, str]) -> dict:
    pid = idea["project_id"]
    return {
        "id": idea["id"], "short_id": idea["id"][:8], "title": idea["title"],
        "status": idea["status"], "origin": idea["origin"], "project_id": pid,
        "project": names.get(pid, pid) if pid else None,
        "note_count": idea["note_count"], "updated_at": idea["updated_at"],
    }


def _page(items: list[dict], names: dict[str, str], *, total: int, offset: int, limit: int,
          elsewhere: int, budget_limited: bool) -> dict:
    returned = len(items)
    has_more = offset + returned < total
    output: dict[str, Any] = {
        "notice": render.NOTICE,
        "count": total, "returned": returned, "offset": offset, "limit": limit,
        "has_more": has_more, "next_offset": offset + returned if has_more else None,
        "budget_limited": budget_limited, "elsewhere": elsewhere,
        "ideas": [_compact(i, names) for i in items],
        "summary": "\n".join(
            render.summary_line(i, names.get(i["project_id"], i["project_id"]) if i["project_id"] else None)
            for i in items
        ),
        "detail_hint": "Kopfzeile, Beschreibung und Anmerkungen einer Idee: idea_read(idea_id=<id>).",
    }
    if elsewhere:
        output["hint"] = (f"{elsewhere} weitere Idee(n) in anderen Projekten oder ohne Projekt: "
                          'project_id="*" zeigt alle.')
    if total == 0:
        output["message"] = "Keine Ideen gefunden."
    elif returned == 0:
        output["message"] = "Keine Ideen auf dieser Seite."
    return output


async def _list(args: dict, ctx: ToolContext) -> ToolResult:
    username = ctx.user_id
    if not username:
        return ToolResult.fail("Kein User-Kontext verfügbar.")
    page = _page_args(args)
    if page is None:
        return ToolResult.fail("Ungültige Seitenangabe: limit muss 1–100, offset mindestens 0 sein.")
    valid, statuses = _statuses(args.get("status"))
    if not valid:
        return ToolResult.fail(render.message("invalid_status") + " Zusätzlich: open, all.")
    limit, offset = page
    project = _project_filter(args, ctx)
    legacy_import.import_for(username)

    total = store.count(username, project=project, statuses=statuses)
    elsewhere = store.count(username, statuses=statuses) - total if project else 0
    items = store.list_ideas(username, project=project, statuses=statuses, limit=limit, offset=offset)
    names = access.project_names(username, access.system_role(username))
    shape = {"total": total, "offset": offset, "limit": limit, "elsewhere": elsewhere}
    output = _page(items, names, **shape, budget_limited=False)
    while items and len(json.dumps(output, ensure_ascii=False)) > _OUTPUT_BUDGET_CHARS:
        items.pop()
        output = _page(items, names, **shape, budget_limited=True)
    return ToolResult.ok(output)


async def _read(args: dict, ctx: ToolContext) -> ToolResult:
    username = ctx.user_id
    if not username:
        return ToolResult.fail("Kein User-Kontext verfügbar.")
    legacy_import.import_for(username)
    idea, error = resolve(username, args.get("idea_id"))
    if idea is None:
        return ToolResult.fail(error)
    pid = idea["project_id"]
    name = access.project_names(username, access.system_role(username)).get(pid, pid) if pid else None
    return ToolResult.ok(render.render_idea(idea, notes.list_for(username, idea["id"]), name))


LIST_TOOL = Tool(
    name="idea_list",
    description=(
        "Listet die Ideen des Nutzers kompakt und seitenweise: Kurz-ID, Status, Herkunft, Projekt, "
        "Kopfzeile. Ohne Angabe gilt das aktive Projekt und nur offene Ideen. Details mit idea_read."
    ),
    schema=_LIST_SCHEMA, execute=_list, category="scratchpad", prompt_hint=_HINT,
)
READ_TOOL = Tool(
    name="idea_read",
    description=(
        "Liest eine Idee des Nutzers vollständig: Kopfzeile, Status, Projekt, Beschreibung und "
        "Anmerkungen. ID vollständig oder als Kurz-ID aus idea_list."
    ),
    schema=_READ_SCHEMA, execute=_read, category="scratchpad",
)
LEGACY_READ_TOOL = Tool(
    name="read_scratchpad",
    description=(
        "Veraltet, nutze idea_list. Der freie Zettel wurde durch einzelne Ideen ersetzt; dieses "
        "Werkzeug liefert dieselbe Liste wie idea_list und bleibt nur für ältere Agenten erhalten."
    ),
    schema=_LIST_SCHEMA, execute=_list, category="scratchpad",
)
