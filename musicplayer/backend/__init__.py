"""Musicplayer-Modul — Backend.

register(ctx) →
  - Router (/api/modules/musicplayer/tracks[...]) — Liste, Streaming (Range),
    Admin-Upload, Admin-Delete
  - Import-Router (/api/modules/musicplayer/generated[...]) — Admin: generierte
    Musik aus den Workspaces auflisten und in den Pool kopieren (R2b)
  - Migrationen (tracks-Tabelle, additiv)

Audio liegt als Datei unter data_dir/modules/musicplayer/ (UUID-Namen),
Metadaten in der DB. Das Frontend ist nur ein Player in der Buddy-Box.
"""
from __future__ import annotations

from .import_routes import router as import_router
from .routes import router


def register(ctx) -> None:
    ctx.register_router(router)
    ctx.register_router(import_router)
    ctx.register_migrations("migrations")
