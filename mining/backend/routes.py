"""Mining-Routen (unter /api/modules/mining, Kern-Gate: module.mining).

GET  /overview          Coin-Tabelle für eine Referenz-GPU oder eigene Hashraten
GET  /gpus              Referenz-GPUs (Kryptex-Angaben)
GET  /config            Einstellungen
PUT  /config            Einstellungen ändern            (mining.control)
POST /refresh           Kryptex sofort abrufen          (mining.control)
"""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from hydrahive.api.middleware.auth import require_auth

from . import clore_store, poller, power, reference, store
from .access import Control
from .profit import usd_per_day

router = APIRouter()
Auth = Annotated[tuple[str, str], Depends(require_auth)]


def _row(q, hashrate: float | None, cfg: dict, eur_rate: float | None) -> dict[str, Any]:
    usd = usd_per_day(q, hashrate or 0, prop_discount=cfg["prop_discount"]) if hashrate else None
    return {
        "coin": q.coin, "name": q.name, "algo": q.algo, "fee": q.fee, "fee_type": q.fee_type,
        "price_usd": q.price_usd, "estimated": q.estimated, "hashrate": hashrate,
        "usd_day": usd, "eur_day": (usd / eur_rate) if (usd is not None and eur_rate) else None,
    }


@router.get("/overview")
def overview(_: Auth, gpu: str = Query("nvidia-rtx-5060-ti-16gb", max_length=64)) -> dict:
    hashrates = reference.hashrates(gpu)
    if hashrates is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "gpu_unknown"})
    cfg = store.get_config()
    quotes, fetched_at = store.load_quotes()
    eur_rate = store.get_usd_per_eur()
    rows = [_row(q, hashrates.get(q.coin), cfg, eur_rate) for q in quotes]
    rows.sort(key=lambda r: (r["usd_day"] is None, -(r["usd_day"] or 0)))
    return {"gpu": gpu, "fetched_at": fetched_at, "usd_per_eur": eur_rate,
            "rows": rows, "reference": reference.meta()}


@router.get("/clore")
def clore_dryrun(_: Auth) -> dict:
    """Clore-Probelauf: letzter Lauf, Treffer 24 h, Tageszusammenfassung (nichts wird gemietet)."""
    return clore_store.summary()


@router.get("/gpus")
def gpus(_: Auth) -> list[dict]:
    return reference.gpus()


@router.get("/config")
def get_config(_: Auth) -> dict:
    return store.get_config()


@router.put("/config")
def put_config(_control: Control, body: dict[str, Any]) -> dict:
    try:
        cfg = store.update_config(body)
    except store.ConfigError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail={"code": str(exc)}) from exc
    if any(k.startswith("power_") for k in body):
        # Quelle sofort lesen — sonst stehen laufende Rigs bis zum nächsten Abfrage-Lauf (30 s)
        # als „Quelle antwortet nicht“. Sync-Route läuft im Threadpool, blockiert keine Event-Loop.
        power.refresh()
    return cfg


@router.post("/refresh")
async def refresh(_control: Control) -> dict:
    count = await poller.refresh()
    return {"coins": count}
