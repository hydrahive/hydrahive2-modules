"""Vitrine-Modul: Gehäuse-Display. E1: Status-Route; der eigentliche Renderer läuft als eigener Dienst
(hydrahive2-vitrine, siehe extension/install.sh), damit das Bild auch bei Neustarts von HydraHive weiterläuft."""
from __future__ import annotations


def register(ctx) -> None:
    from .routes import router
    ctx.register_router(router)
