"""Native internal HydraHive ticket module."""
from __future__ import annotations

from .routes import router


def register(ctx) -> None:
    """Register the ticket router and additive module migrations."""
    ctx.register_router(router)
    ctx.register_migrations("migrations")
