"""Modul TV-Werkstatt – Startbildschirm und Zusätze für Android-TV (SPEC.md, PLAN-E1.md).

Login-Routen unter /api/modules/tvwerkstatt (nur Admins), dazu Geräte-Routen der HydraHive-App unter
/api/module-device/tvwerkstatt (ohne Login, eigener Schlüssel je Gerät; PLAN-APP.md).
"""
from __future__ import annotations

import logging

from .routes import router
from .routes_addons import router as addons_router
from .routes_app_admin import router as app_admin_router
from .routes_app_build import router as app_build_router
from .routes_app_device import app_auth, device_router
from .routes_debloat import router as debloat_router
from .routes_devices import router as devices_router
from .routes_look import router as look_router
from .routes_store import router as store_router

logger = logging.getLogger(__name__)


def register(ctx) -> None:
    ctx.register_migrations("migrations")
    ctx.register_router(devices_router)
    ctx.register_router(look_router)
    ctx.register_router(debloat_router)
    ctx.register_router(store_router)
    ctx.register_router(addons_router)
    ctx.register_router(app_admin_router)
    ctx.register_router(app_build_router)
    if hasattr(ctx, "register_device_router"):          # Geräte-Routen der HydraHive-App (Kern ab #507)
        ctx.register_device_router(device_router, auth=app_auth)
    else:
        logger.warning("TV-Werkstatt: Kern ohne Geräte-Router – die HydraHive-App kann sich nicht verbinden")
    ctx.register_router(router)
