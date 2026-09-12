"""Musicplayer-Modul — projektgebundene Audio-Bibliothek.

register(ctx) →
  - Projekt-Router (`/api/modules/musicplayer/projects/{project_id}/...`) für
    Bibliothek, Upload, Stream/Download und Löschen nach Projekt-RBAC.
  - Import-Router für generierte Musik aus demselben Projektworkspace.
  - Additive Migrationen für Track-Metadaten und Projektzuordnung.

Audio liegt updatefest im jeweiligen Projektworkspace unter `media/audio/`.
Legacy-Dateien aus dem früheren globalen Modulpool werden nach verifizierter Kopie
lazy in den passenden Projektworkspace übernommen.
"""
from __future__ import annotations

from .import_routes import router as import_router
from .routes import router


def register(ctx) -> None:
    ctx.register_router(router)
    ctx.register_router(import_router)
    ctx.register_migrations("migrations")
