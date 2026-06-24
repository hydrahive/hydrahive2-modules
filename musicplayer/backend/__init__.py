"""Musicplayer-Modul — Backend.

register(ctx) →
  - Router (/api/modules/musicplayer/tracks[...]) — Liste, Streaming (Range),
    Admin-Upload, Admin-Delete
  - Migrationen (tracks-Tabelle, additiv)

Audio liegt als Datei unter data_dir/modules/musicplayer/ (UUID-Namen),
Metadaten in der DB. Das Frontend ist nur ein Player in der Buddy-Box.
"""
from __future__ import annotations

from .routes import router


def register(ctx) -> None:
    ctx.register_router(router)
    ctx.register_migrations("migrations")
