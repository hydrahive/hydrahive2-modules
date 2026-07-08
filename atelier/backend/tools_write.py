"""Atelier — Buddy-Anlege-Tools (Ebene B).

Voreinstellen/anlegen von PERSISTIERTER Config über die vorhandenen Atelier-
Funktionen: CI/Stil, Charaktere, Szenen, Drehbuch-Kopf. **Keine Generierung,
kein Render** — nur Config-Dateien schreiben.

Die Backend-Funktionen sanitizen selbst (Längen, Typen), daher sind die Tools
dünne Wrapper. Registrierung über ``ctx.register_tool`` in ``register(ctx)``.
"""
from __future__ import annotations

from hydrahive.tools.base import Tool, ToolContext, ToolResult

from . import characters, screenplay
from .tools_read import _resolve_project

_OPTIONAL_PROJECT = {
    "project_id": {"type": "string", "description": "Optional; Default: aktives Projekt."},
}


# ---- atelier_set_ci ---------------------------------------------------------

async def _set_ci(args: dict, ctx: ToolContext) -> ToolResult:
    pid, err = _resolve_project(ctx, args)
    if err:
        return err
    current = characters.get_ci(pid)
    data = {
        "style_anchor": args.get("style_anchor", current.get("style_anchor")),
        "default_model": args.get("default_model", current.get("default_model")),
        "aspect_ratio": args.get("aspect_ratio", current.get("aspect_ratio")),
        "palette": args.get("palette", current.get("palette")),
    }
    ci = characters.save_ci(pid, data)
    return ToolResult.ok({"project_id": pid, "ci": ci})


SET_CI_TOOL = Tool(
    name="atelier_set_ci",
    description=("Setzt das CI/Stil-Kit eines Projekts: Style-Anchor, Default-"
                "Bildmodell, Aspect-Ratio, Farbpalette. Nur angegebene Felder "
                "ändern sich. Reine Voreinstellung, keine Generierung."),
    schema={
        "type": "object",
        "properties": {
            **_OPTIONAL_PROJECT,
            "style_anchor": {"type": "string", "description": "Projektweiter Stil-Anker (englisch empfohlen)."},
            "default_model": {"type": "string", "description": "Default-Bildmodell (aus atelier_models category=image)."},
            "aspect_ratio": {"type": "string", "description": "z.B. 1:1, 16:9, 9:16, 4:3, 3:4."},
            "palette": {"type": "array", "items": {"type": "string"}, "description": "Farb-Hex-Liste."},
        },
    },
    execute=_set_ci,
    category="atelier",
    prompt_hint="Voreinstellung persistieren. Zeig bei default_model erst atelier_models.",
)


# ---- atelier_character ------------------------------------------------------

_CHARACTER_FIELDS = ("name", "description", "style_anchor", "palette", "seed", "model")


async def _character(args: dict, ctx: ToolContext) -> ToolResult:
    pid, err = _resolve_project(ctx, args)
    if err:
        return err
    action = (args.get("action") or "").strip().lower()

    if action == "create":
        data = {k: args[k] for k in _CHARACTER_FIELDS if k in args}
        if not (data.get("name") or "").strip():
            return ToolResult.fail("Für 'create' braucht die Figur einen Namen.")
        char = characters.create_character(pid, data)
        return ToolResult.ok({"project_id": pid, "character": char})

    if action == "update":
        cid = (args.get("character_id") or "").strip()
        if not cid:
            return ToolResult.fail("'update' braucht character_id (siehe atelier_characters).")
        data = {k: args[k] for k in _CHARACTER_FIELDS if k in args}
        char = characters.update_character(pid, cid, data)
        if char is None:
            return ToolResult.fail(f"Charakter '{cid}' nicht gefunden.")
        return ToolResult.ok({"project_id": pid, "character": char})

    if action == "delete":
        cid = (args.get("character_id") or "").strip()
        if not cid:
            return ToolResult.fail("'delete' braucht character_id.")
        if not characters.delete_character(pid, cid):
            return ToolResult.fail(f"Charakter '{cid}' nicht gefunden.")
        return ToolResult.ok({"project_id": pid, "deleted": cid})

    return ToolResult.fail(f"Unbekannte action '{action}'. Erlaubt: create, update, delete.")


CHARACTER_TOOL = Tool(
    name="atelier_character",
    description=("Legt eine Figur an, ändert oder löscht sie (action: create|"
                "update|delete). Steckbrief: name, description, style_anchor, "
                "palette, seed, model. Referenzbild-Upload NICHT hierüber. "
                "Reine Voreinstellung."),
    schema={
        "type": "object",
        "properties": {
            **_OPTIONAL_PROJECT,
            "action": {"type": "string", "enum": ["create", "update", "delete"]},
            "character_id": {"type": "string", "description": "Bei update/delete nötig."},
            "name": {"type": "string"},
            "description": {"type": "string"},
            "style_anchor": {"type": "string", "description": "Eigener Stil-Anker (sonst Projekt-CI)."},
            "palette": {"type": "array", "items": {"type": "string"}},
            "seed": {"type": "integer", "description": "Fester Seed für Konsistenz (optional)."},
            "model": {"type": "string", "description": "Eigenes Bildmodell (optional)."},
        },
        "required": ["action"],
    },
    execute=_character,
    category="atelier",
    prompt_hint="Erst durchfragen, zusammenfassen, bestätigen lassen — dann anlegen.",
)


# ---- atelier_scene ----------------------------------------------------------

_SCENE_FIELDS = ("title", "description", "character_ids", "dialogues",
                 "music", "camera", "location", "time_of_day")


async def _scene(args: dict, ctx: ToolContext) -> ToolResult:
    pid, err = _resolve_project(ctx, args)
    if err:
        return err
    action = (args.get("action") or "").strip().lower()

    if action == "create":
        data = {k: args[k] for k in _SCENE_FIELDS if k in args}
        scene = screenplay.create_scene(pid, data)
        return ToolResult.ok({"project_id": pid, "scene": scene})

    if action == "update":
        sid = (args.get("scene_id") or "").strip()
        if not sid:
            return ToolResult.fail("'update' braucht scene_id (siehe atelier_scenes).")
        data = {k: args[k] for k in _SCENE_FIELDS if k in args}
        scene = screenplay.update_scene(pid, sid, data)
        if scene is None:
            return ToolResult.fail(f"Szene '{sid}' nicht gefunden.")
        return ToolResult.ok({"project_id": pid, "scene": scene})

    if action == "delete":
        sid = (args.get("scene_id") or "").strip()
        if not sid:
            return ToolResult.fail("'delete' braucht scene_id.")
        if not screenplay.delete_scene(pid, sid):
            return ToolResult.fail(f"Szene '{sid}' nicht gefunden.")
        return ToolResult.ok({"project_id": pid, "deleted": sid})

    if action == "reorder":
        ids = args.get("scene_ids")
        if not isinstance(ids, list) or not ids:
            return ToolResult.fail("'reorder' braucht scene_ids (Liste in neuer Reihenfolge).")
        head = screenplay.reorder_scenes(pid, [str(i) for i in ids])
        return ToolResult.ok({"project_id": pid, "scene_order": head.get("scene_order")})

    return ToolResult.fail(
        f"Unbekannte action '{action}'. Erlaubt: create, update, delete, reorder."
    )


SCENE_TOOL = Tool(
    name="atelier_scene",
    description=("Baut das Drehbuch: Szene anlegen/ändern/löschen/umsortieren "
                "(action: create|update|delete|reorder). Felder: title, "
                "description, character_ids, dialogues [{character_id, line, "
                "emotion}], music {enabled, prompt}, camera, location, "
                "time_of_day. Reine Voreinstellung, kein Render."),
    schema={
        "type": "object",
        "properties": {
            **_OPTIONAL_PROJECT,
            "action": {"type": "string", "enum": ["create", "update", "delete", "reorder"]},
            "scene_id": {"type": "string", "description": "Bei update/delete nötig."},
            "scene_ids": {"type": "array", "items": {"type": "string"},
                          "description": "Bei reorder: Szenen-IDs in neuer Reihenfolge."},
            "title": {"type": "string"},
            "description": {"type": "string"},
            "character_ids": {"type": "array", "items": {"type": "string"}},
            "dialogues": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "character_id": {"type": "string"},
                        "line": {"type": "string"},
                        "emotion": {"type": "string"},
                    },
                },
                "description": "Dialogzeilen der Szene.",
            },
            "music": {
                "type": "object",
                "properties": {
                    "enabled": {"type": "boolean"},
                    "prompt": {"type": "string"},
                },
                "description": "Szenen-Musik-Wunsch (wird beim Rendern erzeugt, nicht hier).",
            },
            "camera": {"type": "object", "description": "Kamera-Preset-Auswahl {group: key}."},
            "location": {"type": "string"},
            "time_of_day": {"type": "string"},
        },
        "required": ["action"],
    },
    execute=_scene,
    category="atelier",
    prompt_hint="Erst durchfragen und bestätigen lassen. Für Charaktere atelier_characters nutzen.",
)


# ---- atelier_set_screenplay -------------------------------------------------

_HEAD_FIELDS = ("title", "logline", "description", "film_model", "audio_model",
                "voice_model", "aspect_ratio", "default_duration")


async def _set_screenplay(args: dict, ctx: ToolContext) -> ToolResult:
    pid, err = _resolve_project(ctx, args)
    if err:
        return err
    current = screenplay.get_screenplay(pid)
    data = {k: args.get(k, current.get(k)) for k in _HEAD_FIELDS}
    head = screenplay.save_screenplay(pid, data)
    return ToolResult.ok({"project_id": pid, "screenplay": head})


SCREENPLAY_TOOL = Tool(
    name="atelier_set_screenplay",
    description=("Setzt den Drehbuch-Kopf: title, logline, description, "
                "film_model, audio_model, voice_model, aspect_ratio, "
                "default_duration. Nur angegebene Felder ändern sich. "
                "Reine Voreinstellung."),
    schema={
        "type": "object",
        "properties": {
            **_OPTIONAL_PROJECT,
            "title": {"type": "string"},
            "logline": {"type": "string"},
            "description": {"type": "string"},
            "film_model": {"type": "string", "description": "Video-Modell (aus atelier_models category=video)."},
            "audio_model": {"type": "string", "description": "Musik-Modell (category=audio)."},
            "voice_model": {"type": "string", "description": "Sprach-Modell (category=speech)."},
            "aspect_ratio": {"type": "string"},
            "default_duration": {"type": "integer", "description": "Default-Shot-Dauer in Sekunden (1-60)."},
        },
    },
    execute=_set_screenplay,
    category="atelier",
    prompt_hint="Modelle vorher mit atelier_models auflisten, nicht raten.",
)


WRITE_TOOLS = [SET_CI_TOOL, CHARACTER_TOOL, SCENE_TOOL, SCREENPLAY_TOOL]
