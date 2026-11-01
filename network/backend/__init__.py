"""Modul Netzwerk (network/PLAN-E1.md, PLAN-020.md) – Zugänge, Sammler, Speicher, Störungen; 0.2.0 Geräte, Clients,
Netz, Verkehr.

register(ctx) → Router /api/modules/network (ansehen: module.network; einrichten: network.configure),
Migrationen, drei Sammler-Jobs (Minute: eigene Messung + FRITZ!Box-Status; 5 min: Dream Machine; stündlich:
Ereignisse, Speedtests, Verlauf). Alles nur lesend.
"""
from __future__ import annotations

from . import collect, routes_admin, routes_config, routes_view


def register(ctx) -> None:
    ctx.register_migrations("migrations")
    ctx.register_router(routes_view.router)
    ctx.register_router(routes_config.router)
    ctx.register_router(routes_admin.router)
    ctx.register_job("network-minute", collect.job_minute, interval_seconds=60, initial_delay_seconds=30)
    ctx.register_job("network-udm", collect.job_udm, interval_seconds=300, initial_delay_seconds=45)
    ctx.register_job("network-hourly", collect.job_hourly, interval_seconds=3600, initial_delay_seconds=90)
