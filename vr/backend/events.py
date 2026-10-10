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
    window = args.get("window")
    if window is not None:
        try:
            w = int(window)
        except (TypeError, ValueError) as exc:
            raise EventError("window muss eine Zahl sein") from exc
        if not 1 <= w <= MAX_WINDOW:
            raise EventError(f"window muss zwischen 1 und {MAX_WINDOW} liegen")
        event["window"] = w
    return event
