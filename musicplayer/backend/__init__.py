"""Mediaplayer-Modul — projektgebundene Audio- und Video-Bibliothek.

register(ctx) bindet Bibliothek, Upload, Stream, Löschen und den sicheren Import
fester Projektquellen ein. Additive Migrationen halten bestehende MP3-Tracks
abspielbar. Medien liegen updatefest unter `media/audio` und `media/video` im
jeweiligen Projektworkspace.
"""
from __future__ import annotations

from .routes import router
from .sources_routes import router as sources_router


def register(ctx) -> None:
    ctx.register_router(router)
    ctx.register_router(sources_router)
    ctx.register_migrations("migrations")
