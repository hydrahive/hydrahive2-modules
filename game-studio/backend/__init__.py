"""Game Studio module registration."""

from __future__ import annotations

from .routes import router
from .workspace_routes import router as workspace_router

router.include_router(workspace_router)


def register(ctx) -> None:
    ctx.register_router(router)
    ctx.register_migrations("migrations")
