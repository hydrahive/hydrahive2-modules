"""Atelier-Modul — Backend.

Media-Generierung mit Charakter-/CI-Konsistenz, projektgebunden. Alles was im
Atelier entsteht, liegt im Workspace des gewählten Projekts unter ``atelier/``.

register(ctx) → Router (/api/modules/atelier/*). Kein DB-Schema: Charaktere,
CI-Kit und Galerie-Metadaten liegen dateibasiert im Projekt-Workspace, damit
sie beim Projekt bleiben und einfach zu sichern/exportieren sind.

Eigener OpenRouter-/api/v1/images-Client (Variante b) — das Core-tool
``generate_image`` bleibt unangetastet.
"""
from __future__ import annotations

from .audio_routes import router as audio_router
from .media_routes import router as media_router
from .routes import router
from .tools_read import READ_TOOLS
from .tools_write import WRITE_TOOLS


def register(ctx) -> None:
    ctx.register_router(router)
    ctx.register_router(media_router)
    ctx.register_router(audio_router)
    # Buddy-Lese-Tools (Ebene A): der Chat-Agent kann das Atelier „sehen".
    for tool in READ_TOOLS:
        ctx.register_tool(tool)
    # Buddy-Anlege-Tools (Ebene B): voreinstellen (CI, Charaktere, Szenen, Kopf) —
    # keine Generierung.
    for tool in WRITE_TOOLS:
        ctx.register_tool(tool)
