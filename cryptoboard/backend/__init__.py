"""Cryptoboard-Modul — Backend.

register(ctx) →
  - Markt-Router    (/api/modules/cryptoboard/{search,markets,top,chart,coin,news})
  - Watchlist-Router(/api/modules/cryptoboard/watchlist)  — per-User
  - Agent-Tool      query_crypto_price
  - Butler-Trigger  crypto_price  + Condition crypto_threshold (F2)
  - Poller-Job      price_poll alle 120s (F1) — emittiert crypto_price-Events
  - Migrationen     (watchlist-Tabelle, additiv)

Automation: Poller liest crypto_price-Trigger aus den Flows, holt Kurse,
emittiert Events; der Nutzer baut Trigger→crypto_threshold→send_email/agent_reply
im bestehenden Butler-Flow-Editor.
"""
from __future__ import annotations

from .routes import router
from .watchlist_routes import router as watchlist_router
from .portfolio_routes import router as portfolio_router
from .analysis_routes import router as analysis_router
# Submodule importieren (NICHT `from .crypto_tool import TOOL`), damit
# `backend.crypto_tool` das Modul bleibt und nicht vom Tool-Objekt überschattet wird.
from . import alerts, crypto_tool


def register(ctx) -> None:
    ctx.register_router(router)
    ctx.register_router(watchlist_router)
    ctx.register_router(portfolio_router)
    ctx.register_router(analysis_router)
    ctx.register_tool(crypto_tool.TOOL)
    ctx.register_butler_trigger(alerts.TRIGGER)
    ctx.register_butler_condition(alerts.CONDITION)
    ctx.register_job("price_poll", alerts.poll, interval_seconds=120, initial_delay_seconds=30)
    ctx.register_migrations("migrations")
