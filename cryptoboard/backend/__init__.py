"""Cryptoboard-Modul — Backend.

register(ctx) →
  - Markt-Router    (/api/modules/cryptoboard/{search,markets,top,chart,coin,news})
  - Watchlist-Router(/api/modules/cryptoboard/watchlist)  — per-User
  - Migrationen     (watchlist-Tabelle, additiv)

Folge-Schritte erweitern um Agent-Tool (query_crypto_price), Poller-Job (F1)
und Butler-Trigger crypto_threshold (F2).
"""
from __future__ import annotations

from .routes import router
from .watchlist_routes import router as watchlist_router


def register(ctx) -> None:
    ctx.register_router(router)
    ctx.register_router(watchlist_router)
    ctx.register_migrations("migrations")
