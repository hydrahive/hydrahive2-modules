"""Mining-Modul — Backend (docs/specs/mining-modul.md im Core-Repo).

E1: Kryptex-Abruf als Hintergrundjob (alle 5 min), Ertragstabelle je
Referenz-GPU, Einstellungen.
E2: Rigs koppeln/freigeben/sperren; Geräte-Routen ohne Nutzer-Login
(braucht Kern mit ``register_device_router``, PR hydrahive2.0#507).
E3–E5: Benchmark je Rig, Entscheider (bester Coin, Schwelle, Mindestlaufzeit),
Miner-Aufträge an die Rigs, Energie-Steuerung (aus / fester Wert / HTTP-Quelle).
"""
from __future__ import annotations

import logging

from . import poller, power
from .device_routes import device_auth, device_router
from .rig_routes import rig_router
from .routes import router

logger = logging.getLogger(__name__)


async def _power_poll() -> None:
    import asyncio
    await asyncio.to_thread(power.refresh)  # Quelle per HTTP lesen, Event-Loop nicht blockieren


def register(ctx) -> None:
    ctx.register_router(router)
    ctx.register_router(rig_router)
    if hasattr(ctx, "register_device_router"):
        ctx.register_device_router(device_router, auth=device_auth)
    else:  # älterer Kern: Ertragstabelle geht, Rigs nicht
        logger.warning("Mining: Kern ohne Geräte-Router — Rigs können sich nicht verbinden (Update nötig)")
    ctx.register_job("kryptex_poll", poller.poll, interval_seconds=poller.INTERVAL_SECONDS,
                     initial_delay_seconds=20)
    ctx.register_job("power_poll", _power_poll, interval_seconds=30, initial_delay_seconds=10)
    ctx.register_migrations("migrations")
