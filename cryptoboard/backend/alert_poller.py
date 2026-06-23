"""DB-Alert-Poller — prüft aktive Alert-Regeln gegen Live-Kurse & Portfolio-Wert.

Läuft als eigener Job. Für jeden aktiven Alert wird der relevante Messwert
geholt (Coin-Kurs / 24h-Änderung bzw. Portfolio-Gesamtwert des Users), die
Crossing-Logik (alert_eval) entscheidet über das Auslösen, und beim Übertritt
wird ein In-App-Event geschrieben. last_value wird immer aktualisiert, damit das
nächste Crossing erkannt werden kann.

Bewusst In-App (Event-Historie + Badge) statt TeamChat/Mail-Direktversand: ein
System-Poller hat keinen Chat-Kontext/Bot-User. Wer Mail/Chat will, baut einen
Butler-Flow über den bestehenden crypto_price-Trigger.
"""
from __future__ import annotations

import logging

from . import alert_eval, alerts_store as store, client, portfolio

logger = logging.getLogger(__name__)

_VS = "eur"


def _collect_coin_ids(alerts: list[dict]) -> list[str]:
    return sorted({
        a["coin_id"] for a in alerts
        if a.get("coin_id") and not store.is_portfolio(a["kind"])
    })


async def _price_map(coin_ids: list[str]) -> dict[str, dict]:
    if not coin_ids:
        return {}
    try:
        rows = await client.markets(_VS, ids=coin_ids)
    except Exception as e:
        logger.warning("cryptoboard alert poll: Kurs-Abruf fehlgeschlagen: %s", e)
        return {}
    return {r["id"]: r for r in rows if r.get("id")}


async def _portfolio_value(user: str, cache: dict[str, float]) -> float | None:
    if user in cache:
        return cache[user]
    try:
        summary = await portfolio.summary(user)
        value = float(summary["totals"]["value"])
    except Exception as e:
        logger.warning("cryptoboard alert poll: Portfolio-Wert für %s fehlgeschlagen: %s", user, e)
        return None
    cache[user] = value
    return value


async def poll() -> None:
    alerts = store.list_active_all()
    if not alerts:
        return

    prices = await _price_map(_collect_coin_ids(alerts))
    pf_cache: dict[str, float] = {}

    for a in alerts:
        kind = a["kind"]
        user = a["user"]

        if store.is_portfolio(kind):
            value = await _portfolio_value(user, pf_cache)
            price = change = None
            portfolio_value = value
        else:
            market = prices.get(a["coin_id"]) or {}
            price = market.get("price")
            change = market.get("change_24h")
            portfolio_value = None

        value = alert_eval.current_value(
            kind, price=price, change_24h=change, portfolio_value=portfolio_value
        )
        if value is None:
            continue

        fired = alert_eval.should_fire(kind, a["threshold"], value, a.get("last_value"))
        if fired:
            msg = alert_eval.format_message(kind, a.get("symbol") or "", a["threshold"], value)
            store.add_event(
                user, alert_id=a["id"], kind=kind, coin_id=a.get("coin_id") or "",
                symbol=a.get("symbol") or "", threshold=a["threshold"], value=value, message=msg,
            )
            logger.info("cryptoboard alert fired (user=%s, id=%s): %s", user, a["id"], msg)
        store.update_state(a["id"], last_value=value, fired=fired)
