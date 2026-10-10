"""Agenten-Werkzeuge: die Brille DES EIGENEN Nutzers ansprechen.

Jedes Werkzeug wirkt nur auf Brillen von ``ToolContext.user_id``. Kein Zugriff
auf Kamera, Mikrofon oder Dateien der Brille.
"""
from __future__ import annotations

from hydrahive.tools.base import Tool, ToolContext, ToolResult

from . import events, state
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


async def _close(args: dict, ctx: ToolContext) -> ToolResult:
    return _send(ctx, events.close_window, args)


async def _layout(args: dict, ctx: ToolContext) -> ToolResult:
    return _send(ctx, events.layout, args)


async def _media(args: dict, ctx: ToolContext) -> ToolResult:
    return _send(ctx, events.media, args)


async def _windows(args: dict, ctx: ToolContext) -> ToolResult:
    s = state.get(ctx.user_id)
    if s is None:
        return ToolResult.ok({"known": False, "connected": hub.connected(ctx.user_id) > 0,
                              "note": "Stand unbekannt – die Brille hat noch nichts gemeldet."})
    return ToolResult.ok({"known": True, "connected": hub.connected(ctx.user_id) > 0, **s})


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
        name="vr_close_window",
        description="Schließt ein Büro-Fenster (1–8) auf der Brille des Nutzers und leert seine Belegung.",
        schema=_obj({"window": {"type": "integer", "minimum": 1, "maximum": events.MAX_WINDOW}}, ["window"]),
        execute=_close,
        category="vr",
    ),
    Tool(
        name="vr_windows",
        description="Liefert, welche HydraVR-App in welchem Büro-Fenster liegt (letzter Bericht der Brille).",
        schema=_obj({}, []),
        execute=_windows,
        category="vr",
    ),
    Tool(
        name="vr_layout",
        description="Richtet das Büro auf einmal ein: Fenster 1..n bekommen die Apps in dieser Reihenfolge, "
                    f"alle übrigen Fenster werden geleert. apps: Liste aus {', '.join(events.APPS)} (max. 8). "
                    "Beispiel Arbeitsmodus: [\"chat\", \"monitor\", \"code\"].",
        schema=_obj({"apps": {"type": "array", "items": {"type": "string", "enum": list(events.APPS)},
                              "minItems": 1, "maxItems": events.MAX_WINDOW}}, ["apps"]),
        execute=_layout,
        category="vr",
    ),
    Tool(
        name="vr_media",
        description="Steuert die Wiedergabe in Film oder Tonstudio auf der Brille: "
                    f"{', '.join(events.MEDIA_ACTIONS)}. app optional (film|music), sonst die gerade spielende.",
        schema=_obj({"action": {"type": "string", "enum": list(events.MEDIA_ACTIONS)},
                     "app": {"type": "string", "enum": list(events.MEDIA_APPS)}}, ["action"]),
        execute=_media,
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
