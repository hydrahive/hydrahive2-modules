"""Zerlege-Werkstatt: autorisierte statische Untersuchung in isolierter Umgebung."""
from __future__ import annotations

from .routes import router


def register(ctx) -> None:
    ctx.register_router(router)
    ctx.register_migrations("migrations")
