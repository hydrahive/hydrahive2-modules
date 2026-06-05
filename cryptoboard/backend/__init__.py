"""Cryptoboard-Modul — Backend.

register(ctx) →
  - Markt-Router (/api/modules/cryptoboard/{search,markets,top,chart,coin})

Folge-Schritte erweitern um News, Watchlist (Migration), Agent-Tool
(query_crypto_price), Poller-Job (F1) und Butler-Trigger crypto_threshold (F2).
"""
from __future__ import annotations

from .routes import router


def register(ctx) -> None:
    ctx.register_router(router)
