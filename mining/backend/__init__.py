"""Mining-Modul — Backend (docs/specs/mining-modul.md im Core-Repo).

E1: Kryptex-Abruf als Hintergrundjob (alle 5 min), Ertragstabelle je
Referenz-GPU, Einstellungen. Rigs/Client folgen in E2.
"""
from __future__ import annotations

from . import poller
from .routes import router


def register(ctx) -> None:
    ctx.register_router(router)
    ctx.register_job("kryptex_poll", poller.poll, interval_seconds=poller.INTERVAL_SECONDS,
                     initial_delay_seconds=20)
    ctx.register_migrations("migrations")
