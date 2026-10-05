"""Buddy-Werkzeug: Ergebnisse des Clore-Probelaufs lesen (in €). Nichts wird gemietet."""
from __future__ import annotations

from hydrahive.tools.base import Tool, ToolContext, ToolResult

from . import clore_store, store

NOTE = ("Nur gerechnet, nichts gemietet: öffentlicher Clore-Marktplatz alle 15 min gegen Kryptex-Ertrag. "
        "„Treffer“ = mindestens 12 % konservatives Plus. Spot ist nur das Mindestgebot.")


def _eur(v: float | None, rate: float | None) -> float | None:
    return round(v / rate, 4) if v is not None and rate else None


def _pct(v: float | None) -> float | None:
    return round(v * 100, 1) if v is not None else None


async def _clore(args: dict, ctx: ToolContext) -> ToolResult:
    s = clore_store.summary()
    rate = store.get_usd_per_eur()
    hits = [{"server_id": h.get("server_id"), "ts": h.get("ts"), "gpu": f"{h.get('count')}× {h.get('gpu')}",
             "coin": h.get("coin"), "hashrate_source": h.get("source"),
             "revenue_eur_day": _eur(h.get("revenue"), rate), "cost_od_eur_day": _eur(h.get("cost_od"), rate),
             "cost_spot_eur_day": _eur(h.get("cost_spot"), rate), "roi_od_pct": _pct(h.get("roi_od")),
             "roi_spot_pct": _pct(h.get("roi_spot")), "reliability": h.get("reliability"), "max_hours": h.get("mrl")}
            for h in s["hits_24h"][:20]]
    days = [{**d, "best_roi_pct": _pct(d.pop("best_roi", None))} for d in s["days"]]
    return ToolResult.ok({"note": NOTE, "last_run": s["last_run"], "hits_24h": hits, "days": days,
                          "enabled": bool(store.get_config().get("clore_dryrun"))})


CLORE_DRYRUN = Tool(
    name="mining_clore_dryrun", category="data", execute=_clore,
    schema={"type": "object", "properties": {}, "required": []},
    description="Mining: Ergebnisse des Clore-Probelaufs – würde sich das Mieten von GPU-Servern bei Clore für "
                "Kryptex-Mining lohnen? Letzter Lauf, beste Treffer der letzten 24 h, Zusammenfassung je Tag. "
                "Es wird nichts gemietet.")
