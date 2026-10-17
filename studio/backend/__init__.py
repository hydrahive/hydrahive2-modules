"""Studio – Backend. Spec: studio/SPEC.md. Etappe 1: Bibliothek (nur lesend)."""
from __future__ import annotations


def register(ctx) -> None:
    from .routes import router
    ctx.register_router(router)
