"""Modul TV-Werkstatt – Startbildschirm und Zusätze für Android-TV (SPEC.md, PLAN-E1.md).

Bausteine 1–3 und 5: Gerüst, Netz mit Sperrliste, Bauumgebung, Fernseher eintragen und prüfen. Bau und
Installation folgen mit den weiteren Bausteinen des Plans.
"""
from __future__ import annotations

from .routes import router
from .routes_debloat import router as debloat_router
from .routes_devices import router as devices_router
from .routes_look import router as look_router
from .routes_store import router as store_router


def register(ctx) -> None:
    ctx.register_migrations("migrations")
    ctx.register_router(devices_router)
    ctx.register_router(look_router)
    ctx.register_router(debloat_router)
    ctx.register_router(store_router)
    ctx.register_router(router)
