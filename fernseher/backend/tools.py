"""Werkzeuge für Agenten (SPEC.md „Werkzeuge für Agenten“). Schaltende Werkzeuge melden den echten neuen Zustand."""
from __future__ import annotations

from hydrahive.tools.base import Tool, ToolContext, ToolResult

from . import client
from .client_errors import TVError


def _fail(exc: TVError) -> ToolResult:
    return ToolResult.fail(f"{exc.code}: {exc}")


async def _status(args: dict, ctx: ToolContext) -> ToolResult:
    try:
        return ToolResult.ok(await client.status())
    except TVError as exc:
        return _fail(exc)


async def _channels(args: dict, ctx: ToolContext) -> ToolResult:
    try:
        chs = await client.channels()
    except TVError as exc:
        return _fail(exc)
    return ToolResult.ok({"count": len(chs), "channels": [{"number": c["number"], "name": c["name"]} for c in chs]})


async def _channel(args: dict, ctx: ToolContext) -> ToolResult:
    try:
        return ToolResult.ok(await client.set_channel(str(args.get("sender") or "")))
    except TVError as exc:
        return _fail(exc)


async def _volume(args: dict, ctx: ToolContext) -> ToolResult:
    try:
        if isinstance(args.get("stumm"), bool):
            return ToolResult.ok(await client.set_mute(args["stumm"]))
        return ToolResult.ok(await client.set_volume(str(args.get("wert") or "")))
    except TVError as exc:
        return _fail(exc)


async def _power(args: dict, ctx: ToolContext) -> ToolResult:
    if not isinstance(args.get("an"), bool):
        return ToolResult.fail("tv_power_invalid: an=true (einschalten) oder an=false (ausschalten) angeben.")
    try:
        return ToolResult.ok(await client.set_power(args["an"]))
    except TVError as exc:
        return _fail(exc)


async def _app(args: dict, ctx: ToolContext) -> ToolResult:
    name = str(args.get("name") or "").strip()
    try:
        if not name:
            return ToolResult.ok({"apps": [a["name"] for a in await client.apps()]})
        return ToolResult.ok(await client.start_app(name))
    except TVError as exc:
        return _fail(exc)


def _obj(props: dict, required: list[str] | None = None) -> dict:
    return {"type": "object", "properties": props, "required": required or []}


ALL = [
    Tool(name="tv_status", category="read", schema=_obj({}), execute=_status,
         description="Zeigt, ob der Fernseher an ist, welcher Sender und welche Sendung läuft und wie laut er ist."),
    Tool(name="tv_sender_liste", category="read", schema=_obj({}), execute=_channels,
         description="Listet alle Fernsehsender mit Platz und Name."),
    Tool(name="tv_sender", category="action", execute=_channel,
         schema=_obj({"sender": {"type": "string", "description": "Sendername (z. B. 'ZDF', 'kabel eins') oder "
                                                               "Platz (z. B. '2')."}}, ["sender"]),
         description="Schaltet den Fernseher auf einen Sender. Bei mehreren passenden Sendern kommt eine Liste – "
                     "dann nachfragen statt raten."),
    Tool(name="tv_lautstaerke", category="action", execute=_volume,
         schema=_obj({"wert": {"type": "string", "description": "Neue Lautstärke 0–100 oder relativ '+3' / '-5'."},
                      "stumm": {"type": "boolean", "description": "true = stumm, false = Ton wieder an."}}),
         description="Ändert die Lautstärke oder schaltet stumm. Es gibt eine Obergrenze und höchstens 20 Schritte "
                     "auf einmal (Schutz vor zu laut). Leiser geht immer, auch über der Grenze. Läuft der Ton über "
                     "den Receiver (output receiver im Status), ist das dessen Lautstärke."),
    Tool(name="tv_power", category="action", execute=_power,
         schema=_obj({"an": {"type": "boolean", "description": "true = einschalten, false = ausschalten."}}, ["an"]),
         description="Schaltet den Fernseher ein oder aus (Standby)."),
    Tool(name="tv_app", category="action", execute=_app,
         schema=_obj({"name": {"type": "string", "description": "App-Name, z. B. 'Plex', 'Netflix'. Leer = Liste."}}),
         description="Startet eine App auf dem Fernseher. Ohne Namen kommt die Liste der installierten Apps."),
]
