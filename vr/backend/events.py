"""Ereignisse an die Brille bauen und prüfen (eine Stelle für alle Grenzen)."""
from __future__ import annotations

MAX_TEXT = 2000
MAX_TITLE = 120
MAX_WINDOW = 8
# Muss zur App-Liste in HydraVR (office/AppCatalog.kt) passen.
APPS = ("chat", "monitor", "film", "storyboard", "music", "book", "tasks", "desktop", "browser", "code")


class EventError(ValueError):
    """Ungültige Eingabe — wird dem Agenten als Fehler gemeldet."""


def _text(value: object, name: str, limit: int) -> str:
    text = str(value or "").strip()
    if not text:
        raise EventError(f"{name} darf nicht leer sein")
    if len(text) > limit:
        raise EventError(f"{name} ist zu lang (max. {limit} Zeichen)")
    return text


def say(args: dict) -> dict:
    return {"type": "say", "text": _text(args.get("text"), "text", MAX_TEXT)}


def notify(args: dict) -> dict:
    return {
        "type": "notify",
        "title": _text(args.get("title"), "title", MAX_TITLE),
        "text": _text(args.get("text"), "text", MAX_TEXT),
    }


def open_app(args: dict) -> dict:
    app = str(args.get("app") or "").strip()
    if app not in APPS:
        raise EventError(f"app muss eine von {', '.join(APPS)} sein")
    event: dict = {"type": "open_app", "app": app}
    if args.get("window") is not None:
        event["window"] = _window(args.get("window"))
    return event


MEDIA_ACTIONS = ("play", "pause", "stop", "next", "volume_up", "volume_down")
MEDIA_APPS = ("film", "music")


def _window(value: object) -> int:
    try:
        w = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise EventError("window muss eine Zahl sein") from exc
    if not 1 <= w <= MAX_WINDOW:
        raise EventError(f"window muss zwischen 1 und {MAX_WINDOW} liegen")
    return w


def close_window(args: dict) -> dict:
    return {"type": "close_window", "window": _window(args.get("window"))}


def layout(args: dict) -> dict:
    apps = args.get("apps")
    if not isinstance(apps, list) or not apps:
        raise EventError("apps muss eine nicht leere Liste sein")
    if len(apps) > MAX_WINDOW:
        raise EventError(f"höchstens {MAX_WINDOW} Apps")
    bad = [a for a in apps if a not in APPS]
    if bad:
        raise EventError(f"unbekannte App: {', '.join(map(str, bad))} (erlaubt: {', '.join(APPS)})")
    return {"type": "layout", "apps": list(apps)}


def media(args: dict) -> dict:
    action = str(args.get("action") or "")
    if action not in MEDIA_ACTIONS:
        raise EventError(f"action muss eine von {', '.join(MEDIA_ACTIONS)} sein")
    event: dict = {"type": "media", "action": action}
    app = args.get("app")
    if app is not None:
        if app not in MEDIA_APPS:
            raise EventError(f"app muss {' oder '.join(MEDIA_APPS)} sein")
        event["app"] = app
    return event
