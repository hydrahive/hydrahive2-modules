"""Atelier — Buddy-Lese-Tools (Ebene A).

Dünne Wrapper um die vorhandenen Atelier-Funktionen, damit der Chat-Agent das
Atelier „sehen" kann: Projekte, Modell-Listen (A–Z je Kategorie), Projekt-
Snapshot, Charaktere, Galerie, Szenen. **Keine Generierung, keine Änderung** —
reine Leseoperationen.

Registrierung über ``ctx.register_tool`` in ``register(ctx)``.
"""
from __future__ import annotations

from hydrahive.llm.media_models import (
    list_audio_models, list_image_models, list_speech_models, list_video_models,
)
from hydrahive.projects._config_io import list_for_user
from hydrahive.tools.base import Tool, ToolContext, ToolResult

from . import characters, screenplay, service, storage

_MODEL_LISTERS = {
    "image": list_image_models,
    "video": list_video_models,
    "audio": list_audio_models,
    "speech": list_speech_models,
}


def _resolve_project(ctx: ToolContext, args: dict) -> tuple[str | None, ToolResult | None]:
    """Ermittelt die project_id (Argument > aktives Projekt) und prüft Zugriff.

    Gibt (project_id, None) bei Erfolg oder (None, fail-Result) bei Fehler.
    """
    pid = (args.get("project_id") or ctx.project_id or "").strip()
    if not pid:
        return None, ToolResult.fail(
            "Kein Projekt gewählt. Öffne ein Projekt oder gib project_id an "
            "(atelier_projects listet die verfügbaren)."
        )
    if not storage.is_project_id(pid) or not storage.user_can_access(ctx.user_id, pid):
        return None, ToolResult.fail(f"Kein Zugriff auf Projekt '{pid}'.")
    return pid, None


# ---- atelier_projects -------------------------------------------------------

async def _projects(_args: dict, ctx: ToolContext) -> ToolResult:
    projects = [{"id": p["id"], "name": p.get("name") or p["id"]}
                for p in list_for_user(ctx.user_id)]
    return ToolResult.ok({"projects": projects, "active": ctx.project_id})


PROJECTS_TOOL = Tool(
    name="atelier_projects",
    description=("Listet die Atelier-Projekte des Users (id + name) und welches "
                "gerade aktiv ist. Erster Schritt, um Kontext zu holen."),
    schema={"type": "object", "properties": {}},
    execute=_projects,
    category="atelier",
    prompt_hint="Reines Lesen. Nutze das zuerst, um zu wissen, welches Projekt gemeint ist.",
)


# ---- atelier_models ---------------------------------------------------------

async def _models(args: dict, _ctx: ToolContext) -> ToolResult:
    cat = (args.get("category") or "").strip().lower()
    lister = _MODEL_LISTERS.get(cat)
    if lister is None:
        return ToolResult.fail(
            f"Unbekannte Kategorie '{cat}'. Erlaubt: image, video, audio, speech."
        )
    models = await lister()
    models = sorted(models, key=lambda m: (m.get("name") or m.get("id") or "").lower())
    return ToolResult.ok({"category": cat, "count": len(models), "models": models})


MODELS_TOOL = Tool(
    name="atelier_models",
    description=("Listet die verfügbaren Modelle einer Kategorie (image, video, "
                "audio, speech) als A–Z-Liste — genau die Auswahl wie in den "
                "Atelier-Dropdowns. Bei Video zusätzlich Dauern/Formate/Frame-Typen."),
    schema={
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "enum": ["image", "video", "audio", "speech"],
                "description": "Welche Modell-Kategorie aufgelistet werden soll.",
            },
        },
        "required": ["category"],
    },
    execute=_models,
    category="atelier",
    prompt_hint="Zeig dem User die Liste, statt ein Modell zu raten. Reines Lesen.",
)


# ---- atelier_overview -------------------------------------------------------

async def _overview(args: dict, ctx: ToolContext) -> ToolResult:
    pid, err = _resolve_project(ctx, args)
    if err:
        return err
    ci = characters.get_ci(pid)
    chars = characters.list_characters(pid)
    gallery = service.scan_gallery(pid)
    scenes = screenplay.list_scenes(pid)
    head = screenplay.get_screenplay(pid)
    return ToolResult.ok({
        "project_id": pid,
        "ci": ci,
        "screenplay": {k: head.get(k) for k in
                       ("title", "logline", "film_model", "audio_model",
                        "voice_model", "aspect_ratio", "default_duration")},
        "counts": {
            "characters": len(chars),
            "gallery_images": len(gallery),
            "scenes": len(scenes),
        },
    })


OVERVIEW_TOOL = Tool(
    name="atelier_overview",
    description=("Snapshot eines Atelier-Projekts: CI/Stil, Drehbuch-Kopf und "
                "Anzahl Charaktere/Bilder/Szenen. Für 'lies mein Atelier'."),
    schema={
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "Optional; Default: aktives Projekt."},
        },
    },
    execute=_overview,
    category="atelier",
    prompt_hint="Reines Lesen. Guter zweiter Schritt nach atelier_projects.",
)


# ---- atelier_characters -----------------------------------------------------

async def _characters(args: dict, ctx: ToolContext) -> ToolResult:
    pid, err = _resolve_project(ctx, args)
    if err:
        return err
    chars = characters.list_characters(pid)
    out = [{
        "id": c["id"], "name": c.get("name"), "description": c.get("description"),
        "style_anchor": c.get("style_anchor"), "seed": c.get("seed"),
        "model": c.get("model"), "reference_count": len(c.get("references") or []),
    } for c in chars]
    return ToolResult.ok({"project_id": pid, "characters": out})


CHARACTERS_TOOL = Tool(
    name="atelier_characters",
    description="Listet die Charaktere eines Projekts mit Steckbrief (Name, Beschreibung, Stil, Seed, Modell, #Referenzen).",
    schema={
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "Optional; Default: aktives Projekt."},
        },
    },
    execute=_characters,
    category="atelier",
    prompt_hint="Reines Lesen.",
)


# ---- atelier_gallery --------------------------------------------------------

async def _gallery(args: dict, ctx: ToolContext) -> ToolResult:
    pid, err = _resolve_project(ctx, args)
    if err:
        return err
    limit = args.get("limit")
    items = service.scan_gallery(pid)
    if isinstance(limit, int) and limit > 0:
        items = items[:limit]
    out = [{
        "rel": it["rel"], "prompt": it.get("prompt"), "seed": it.get("seed"),
        "model": it.get("model"), "created_at": it.get("created_at"),
    } for it in items]
    return ToolResult.ok({"project_id": pid, "count": len(out), "images": out})


GALLERY_TOOL = Tool(
    name="atelier_gallery",
    description="Listet die generierten Galerie-Bilder eines Projekts (rel, Prompt, Seed, Modell) — z.B. um Prompts wiederzuverwenden.",
    schema={
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "Optional; Default: aktives Projekt."},
            "limit": {"type": "integer", "description": "Optional; max. Anzahl (neueste zuerst)."},
        },
    },
    execute=_gallery,
    category="atelier",
    prompt_hint="Reines Lesen.",
)


# ---- atelier_scenes ---------------------------------------------------------

async def _scenes(args: dict, ctx: ToolContext) -> ToolResult:
    pid, err = _resolve_project(ctx, args)
    if err:
        return err
    head = screenplay.get_screenplay(pid)
    scenes = screenplay.list_scenes(pid)
    return ToolResult.ok({"project_id": pid, "screenplay": head, "scenes": scenes})


SCENES_TOOL = Tool(
    name="atelier_scenes",
    description="Liest den Drehbuch-Kopf und die Szenen-Liste eines Projekts (Regie-Tab).",
    schema={
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "Optional; Default: aktives Projekt."},
        },
    },
    execute=_scenes,
    category="atelier",
    prompt_hint="Reines Lesen.",
)


READ_TOOLS = [
    PROJECTS_TOOL, MODELS_TOOL, OVERVIEW_TOOL,
    CHARACTERS_TOOL, GALLERY_TOOL, SCENES_TOOL,
]
