"""Modul TV-Werkstatt – Startbildschirm und Zusätze für Android-TV (SPEC.md, PLAN-E1.md).

Baustein 1: Gerüst, Zugriff nur für Admins, Tabellen. Netz, Container, Bau, Geräte und Installation folgen mit den
weiteren Bausteinen des Plans.
"""
from __future__ import annotations

from .routes import router


def register(ctx) -> None:
    ctx.register_migrations("migrations")
    ctx.register_router(router)
