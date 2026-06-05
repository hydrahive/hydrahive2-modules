"""Crypto-Alerts — Butler-Trigger crypto_price + Condition crypto_threshold + Poller.

Der Poller (F1-Job) liest aus den Butler-Flows, welche Coins überwacht werden
(crypto_price-Trigger), holt deren Kurse und emittiert pro Coin ein
crypto_price-Event in die Butler-Engine. Der crypto_threshold-Condition prüft,
ob der Kurs die konfigurierte Schwelle in DIESER Aktualisierung gekreuzt hat —
feuert also nur am Übertritt, nicht in jedem Tick darüber/darunter.

So baut der Nutzer im bestehenden Butler-Flow-Editor:
  Trigger crypto_price(coin) → Condition crypto_threshold(direction, price)
    → Action send_email / agent_reply (Bericht).

Preise in EUR (Modul-Default); Schwellen-Preise im Flow sind in EUR zu setzen.
Letzter Preis pro Coin im Speicher — kein Catch-up über Neustarts.
"""
from __future__ import annotations

import logging

from hydrahive.butler.executor import dispatch_event
from hydrahive.butler.models import TriggerEvent
from hydrahive.butler.persistence import list_flows
from hydrahive.butler.registry import ConditionSpec, ParamSchema, TriggerSpec

from . import client

logger = logging.getLogger(__name__)

_VS = "eur"
_last_price: dict[str, float] = {}


# ---------------------------------------------------------------- Trigger
def _match_price(params: dict, event: TriggerEvent) -> bool:
    if event.event_type != "crypto_price":
        return False
    want = (params.get("coin_id") or "").strip().lower()
    return not want or want == (event.payload.get("coin_id") or "")


TRIGGER = TriggerSpec(
    subtype="crypto_price",
    label="Krypto-Kurs",
    description="Feuert bei jeder Kurs-Aktualisierung des gewählten Coins (CoinGecko-ID).",
    params=[
        ParamSchema(key="coin_id", label="Coin (CoinGecko-ID)", kind="text",
                    required=True, placeholder="bitcoin"),
    ],
    matches=_match_price,
)


# -------------------------------------------------------------- Condition
def _eval_threshold(params: dict, event: TriggerEvent) -> bool:
    try:
        threshold = float(params.get("price"))
    except (TypeError, ValueError):
        return False
    direction = (params.get("direction") or "above").strip().lower()
    price = event.payload.get("price")
    prev = event.payload.get("prev_price")
    if price is None or prev is None:
        return False
    if direction == "below":
        return prev > threshold >= price
    return prev < threshold <= price


CONDITION = ConditionSpec(
    subtype="crypto_threshold",
    label="Kurs-Schwelle gekreuzt",
    description="Wahr genau dann, wenn der Kurs die Schwelle in dieser Aktualisierung über-/unterschritten hat.",
    params=[
        ParamSchema(key="direction", label="Richtung", kind="select", required=True,
                    options=["above", "below"], default="above"),
        ParamSchema(key="price", label="Schwelle (EUR)", kind="number", required=True,
                    placeholder="100000"),
    ],
    evaluate=_eval_threshold,
)


# ----------------------------------------------------------------- Poller
def _watched_coins() -> set[str]:
    coins: set[str] = set()
    for flow in list_flows(owner=None):
        if not flow.enabled:
            continue
        for n in flow.nodes:
            if n.type == "trigger" and n.subtype == "crypto_price":
                cid = (n.params.get("coin_id") or "").strip().lower()
                if cid:
                    coins.add(cid)
    return coins


async def poll() -> None:
    coins = _watched_coins()
    if not coins:
        return
    try:
        rows = await client.markets(_VS, ids=sorted(coins))
    except Exception as e:
        logger.warning("cryptoboard poll: Kurs-Abruf fehlgeschlagen: %s", e)
        return
    for r in rows:
        cid = r.get("id")
        price = r.get("price")
        if not cid or price is None:
            continue
        prev = _last_price.get(cid, price)
        _last_price[cid] = price
        event = TriggerEvent(
            event_type="crypto_price",
            payload={
                "coin_id": cid, "price": price, "prev_price": prev,
                "change_24h": r.get("change_24h"), "symbol": r.get("symbol"),
            },
        )
        try:
            await dispatch_event(event, owner=None)
        except Exception as e:
            logger.warning("cryptoboard poll: dispatch %s fehlgeschlagen: %s", cid, e)
