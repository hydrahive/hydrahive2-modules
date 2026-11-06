"""Game Studio module registration."""

from __future__ import annotations

from .routes import router


def register(ctx) -> None:
    ctx.register_router(router)
    ctx.register_migrations("migrations")
