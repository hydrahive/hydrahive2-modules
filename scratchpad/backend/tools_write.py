"""Schreib-Werkzeug idea_write.

Der Agent legt eigene Ideen an, hängt Anmerkungen an und setzt den Status.
Kopfzeile und Beschreibung einer Idee des Nutzers ändert er nie: dafür gibt
es die Anmerkung. Geprüft wird alles vor dem ersten Schreiben, damit ein
abgelehnter Aufruf nichts halb hinterlässt.
"""
from __future__ import annotations

import logging

from hydrahive.tools.base import Tool, ToolContext, ToolResult

from . import access, notes, render, store
from ._ids import resolve

logger = logging.getLogger(__name__)

_SCHEMA = {
    "type": "object",
    "properties": {
        "idea_id": {"type": "string",
                    "description": "Vorhandene Idee (ID oder Kurz-ID). Weglassen, um eine neue Idee anzulegen."},
        "title": {"type": "string",
                  "description": "Kopfzeile: was es werden soll (höchstens 200 Zeichen). Pflicht bei neuer Idee. "
                                 "Bei vorhandenen Ideen nur änderbar, wenn sie vom Agenten stammen."},
        "body": {"type": "string",
                 "description": "Beschreibung (Markdown). Bei vorhandenen Ideen nur änderbar, wenn sie vom "
                                "Agenten stammen."},
        "note": {"type": "string",
                 "description": "Anmerkung an eine vorhandene Idee. Der Text des Nutzers bleibt unverändert."},
        "status": {"type": "string", "enum": list(store.STATUSES),
                   "description": "Status setzen. Der Wechsel wird als Anmerkung festgehalten."},
        "project_id": {"type": "string",
                       "description": "Nur bei neuer Idee: Projekt-ID, 'none' = ohne Projekt. "
                                      "Ohne Angabe das aktive Projekt des Laufs."},
    },
}
_PROTECTED = (
    "Diese Idee stammt vom Nutzer. Kopfzeile und Beschreibung änderst du nicht. "
    "Schreibe deinen Vorschlag als Anmerkung: idea_write(idea_id=…, note=…)."
)


def agent_name(ctx: ToolContext) -> str | None:
    """Anzeigename des Agenten für die Anmerkung, sofern die Konfiguration lesbar ist."""
    from hydrahive.agents import config as agent_config

    try:
        cfg = agent_config.get(ctx.agent_id or "")
    except (OSError, ValueError):
        logger.warning("scratchpad: Agenten-Konfiguration %s nicht lesbar", ctx.agent_id)
        return None
    return (cfg or {}).get("name") or None


def _text(args: dict, key: str) -> tuple[bool, str | None]:
    """(gültig, Wert). Fehlt der Schlüssel, ist der Wert ``None``."""
    if key not in args or args[key] is None:
        return True, None
    return (True, args[key]) if isinstance(args[key], str) else (False, None)


def _result(idea: dict, created: bool, extra: str = "") -> ToolResult:
    compact = {key: idea[key] for key in ("id", "title", "status", "origin", "project_id")}
    compact["short_id"] = idea["id"][:8]
    verb = "angelegt" if created else "aktualisiert"
    summary = f"Idee {compact['short_id']} {verb}: {idea['title']} ({render.status_label(idea['status'])})"
    output = {"created": created, "idea": compact, "summary": summary}
    if extra:
        output["hinweis"] = extra
    return ToolResult.ok(output)


def _create(username: str, ctx: ToolContext, fields: dict) -> ToolResult:
    if fields["note"] is not None:
        return ToolResult.fail("note geht nur mit idea_id. Bei einer neuen Idee gehört der Text in body.")
    wanted = (fields["project_id"] or "").strip()
    project = None if wanted == store.NO_PROJECT else (wanted or ctx.project_id or None)
    status = fields["status"]
    if status is not None and status not in store.STATUSES:
        return ToolResult.fail(render.message("invalid_status"))
    try:
        project = access.check_project(username, access.system_role(username), project)
        idea = store.create(username, title=fields["title"], body=fields["body"] or "",
                            project_id=project, origin="agent")
        if status and status != idea["status"]:
            idea = store.update(username, idea["id"], status=status) or idea
    except store.IdeaError as exc:
        return ToolResult.fail(render.message(exc.code))
    return _result(idea, created=True)


def _update(username: str, ctx: ToolContext, fields: dict) -> ToolResult:
    idea, error = resolve(username, fields["idea_id"])
    if idea is None:
        return ToolResult.fail(error)
    title, body, note, status = fields["title"], fields["body"], fields["note"], fields["status"]
    if (title is not None or body is not None) and idea["origin"] != "agent":
        return ToolResult.fail(_PROTECTED)
    if title is None and body is None and note is None and status is None:
        return ToolResult.fail("Nichts zu tun: note, status oder (bei Ideen vom Agenten) title/body angeben.")
    if status is not None and status not in store.STATUSES:
        return ToolResult.fail(render.message("invalid_status"))
    try:
        if note is not None and not note.strip():
            raise store.IdeaError("note_required")
        if note is not None and len(note.strip()) > notes.MAX_NOTE:
            raise store.IdeaError("note_too_long")
        changes = {key: value for key, value in (("title", title), ("body", body)) if value is not None}
        if title is not None:
            store.clean_title(title)
        if body is not None:
            store.check_body(body)
        who = agent_name(ctx)
        if status is not None and status != idea["status"]:
            changes["status"] = status
        if changes:
            store.update(username, idea["id"], **changes)
        if "status" in changes:
            line = f"Status: {render.status_label(idea['status'])} → {render.status_label(status)}"
            notes.add(username, idea["id"], author="system", body=line, agent_name=who)
        if note is not None:
            notes.add(username, idea["id"], author="agent", body=note, agent_name=who)
    except store.IdeaError as exc:
        return ToolResult.fail(render.message(exc.code))
    extra = "project_id gilt nur beim Anlegen und wurde nicht geändert." if fields["project_id"] else ""
    return _result(store.get(username, idea["id"]) or idea, created=False, extra=extra)


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    username = ctx.user_id
    if not username:
        return ToolResult.fail("Kein User-Kontext verfügbar.")
    fields: dict = {}
    for key in ("idea_id", "title", "body", "note", "status", "project_id"):
        valid, fields[key] = _text(args, key)
        if not valid:
            return ToolResult.fail(f"{key} muss ein Text sein.")
    if (fields["idea_id"] or "").strip():
        return _update(username, ctx, fields)
    return _create(username, ctx, fields)


WRITE_TOOL = Tool(
    name="idea_write",
    description=(
        "Ohne idea_id: legt eine neue Idee an (Herkunft Agent, title Pflicht). Mit idea_id: hängt mit "
        "note eine Anmerkung an und/oder setzt mit status den Status. Kopfzeile und Beschreibung einer "
        "Idee des Nutzers lassen sich nicht ändern, nur die von Ideen des Agenten."
    ),
    schema=_SCHEMA, execute=_execute, category="scratchpad",
)
