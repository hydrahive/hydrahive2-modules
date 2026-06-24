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
from .import_routes import router as import_router
from .analysis_routes import router as analysis_router
from .alerts_routes import router as alerts_router
from .valuation_routes import router as valuation_router
# Submodule importieren (NICHT `from .crypto_tool import TOOL`), damit
# `backend.crypto_tool` das Modul bleibt und nicht vom Tool-Objekt überschattet wird.
from . import alerts, alert_poller, crypto_tool, portfolio_tool, analysis_tool


def register(ctx) -> None:
    ctx.register_router(router)
    ctx.register_router(watchlist_router)
    ctx.register_router(portfolio_router)
    ctx.register_router(import_router)
    ctx.register_router(analysis_router)
    ctx.register_router(alerts_router)
    ctx.register_router(valuation_router)
    ctx.register_tool(crypto_tool.TOOL)
    ctx.register_tool(portfolio_tool.TOOL)
    ctx.register_tool(analysis_tool.TOOL)
    ctx.register_butler_trigger(alerts.TRIGGER)
    ctx.register_butler_condition(alerts.CONDITION)
    ctx.register_job("price_poll", alerts.poll, interval_seconds=120, initial_delay_seconds=30)
    ctx.register_job("alert_poll", alert_poller.poll, interval_seconds=120, initial_delay_seconds=45)
    ctx.register_migrations("migrations")
