"""Agenten-Werkzeuge: die Brille DES EIGENEN Nutzers ansprechen.

Jedes Werkzeug wirkt nur auf Brillen von ``ToolContext.user_id``. Kein Zugriff
auf Kamera, Mikrofon oder Dateien der Brille.
"""
from __future__ import annotations

from hydrahive.tools.base import Tool, ToolContext, ToolResult

from . import events
from .hub import hub

NO_HEADSET = ("Keine VR-Brille verbunden — HydraVR ist bei diesem Nutzer gerade nicht offen. "
              "Nichts wurde zugestellt.")


def _send(ctx: ToolContext, build, args: dict) -> ToolResult:
    try:
        event = build(args)
    except events.EventError as exc:
        return ToolResult.fail(str(exc))
    if hub.publish(ctx.user_id, event) == 0:
        return ToolResult.fail(NO_HEADSET)
    return ToolResult.ok({"delivered": True, "event": event["type"]})


async def _say(args: dict, ctx: ToolContext) -> ToolResult:
    return _send(ctx, events.say, args)


async def _notify(args: dict, ctx: ToolContext) -> ToolResult:
    return _send(ctx, events.notify, args)


async def _open_app(args: dict, ctx: ToolContext) -> ToolResult:
    return _send(ctx, events.open_app, args)


async def _status(args: dict, ctx: ToolContext) -> ToolResult:
    n = hub.connected(ctx.user_id)
    return ToolResult.ok({"connected": n > 0, "headsets": n})


def _obj(props: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": props, "required": required}


TOOLS = [
    Tool(
        name="vr_say",
        description="Spricht einen kurzen Text auf der VR-Brille des Nutzers (Sprachausgabe). "
                    "Nur verwenden, wenn der Nutzer gerade in VR ist (vr_status) und es passt.",
        schema=_obj({"text": {"type": "string", "description": "Was gesagt werden soll (max. 2000 Zeichen)"}},
                    ["text"]),
        execute=_say,
        category="vr",
    ),
    Tool(
        name="vr_notify",
        description="Zeigt eine Benachrichtigung im HydraVR-Hauptmenü der Brille des Nutzers.",
        schema=_obj({"title": {"type": "string"}, "text": {"type": "string"}}, ["title", "text"]),
        execute=_notify,
        category="vr",
    ),
    Tool(
        name="vr_open_app",
        description="Öffnet eine HydraVR-App in einem Büro-Fenster der Brille des Nutzers. "
                    f"app: {', '.join(events.APPS)}. window: 1–8 (optional, sonst erstes passendes/freies).",
        schema=_obj({"app": {"type": "string", "enum": list(events.APPS)},
                     "window": {"type": "integer", "minimum": 1, "maximum": events.MAX_WINDOW}}, ["app"]),
        execute=_open_app,
        category="vr",
    ),
    Tool(
        name="vr_status",
        description="Prüft, ob der Nutzer gerade eine VR-Brille mit HydraVR verbunden hat.",
        schema=_obj({}, []),
        execute=_status,
        category="vr",
    ),
]
