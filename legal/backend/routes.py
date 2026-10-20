"""Routen /api/modules/legal/… (Plan L1 Schritt 6).

Das Kern-Tor davor (``api/main.py`` mount_module_routers) prüft die Freigabe ``module.legal`` und – weil das
Manifest ``"vault": true`` setzt – die Vault-PIN. Hier: Login (``require_auth``) und Admin für den Abgleich.
"""
from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from hydrahive.api.middleware.auth import require_admin, require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.db.connection import db

from . import corpus_list, corpus_store, corpus_sync, norm_view, search

router = APIRouter()
Auth = Annotated[tuple[str, str], Depends(require_auth)]
Admin = Annotated[tuple[str, str], Depends(require_admin)]
_tasks: set[asyncio.Task] = set()


def _norm_counts() -> dict[str, int]:
    with db() as c:
        return dict(c.execute("SELECT law_key, count(*) FROM module_legal_norms WHERE valid_to IS NULL "
                              "GROUP BY law_key").fetchall())


@router.get("/laws")
def laws(_: Auth) -> dict:
    counts = _norm_counts()
    items = [{**law, "norms": counts.get(law["key"], 0), "group": corpus_list.group_of(law["key"])}
             for law in corpus_store.list_laws()]
    return {"laws": items, "core_total": len(corpus_list.core_keys()), "groups": list(corpus_list.CORE)}


@router.get("/laws/{key}")
def law_detail(key: str, _: Auth) -> dict:
    law = corpus_store.get_law(key)
    if law is None:
        raise coded(status.HTTP_404_NOT_FOUND, "legal_law_not_found", key=key)
    with db() as c:
        rows = c.execute("SELECT enbez, title, gliederung FROM module_legal_norms WHERE law_key = ? "
                         "AND valid_to IS NULL ORDER BY position", (key,)).fetchall()
    return {**law, "norms": [{"enbez": e, "title": t, "gliederung": g} for e, t, g in rows]}


@router.get("/norm")
def norm(_: Auth, citation: Annotated[str, Query(min_length=1, max_length=120)],
         as_of: Annotated[str | None, Query(max_length=30)] = None) -> dict:
    try:
        return norm_view.lookup(citation, as_of=as_of)
    except norm_view.NormError as e:
        code = status.HTTP_404_NOT_FOUND if e.code in ("not_found", "unknown_law") else 422
        raise coded(code, f"legal_{e.code}", message=str(e)) from None


@router.get("/search")
def search_route(_: Auth, q: Annotated[str, Query(max_length=500)],
                 law: Annotated[str | None, Query(max_length=40)] = None,
                 limit: Annotated[int, Query(ge=1, le=search.MAX_LIMIT)] = 10) -> dict:
    try:
        return {"hits": search.search(q, law=law, limit=limit)}
    except search.SearchError as e:
        raise coded(422, "legal_search_invalid", message=str(e)) from None


@router.get("/sync")
def sync_status(_: Auth) -> dict:
    return {"last": corpus_sync.last_run(), "running": corpus_sync._RUNNING}


@router.post("/sync", status_code=status.HTTP_202_ACCEPTED)
async def sync_now(_: Admin) -> dict:
    if corpus_sync._RUNNING:
        raise coded(status.HTTP_409_CONFLICT, "legal_sync_running")
    task = asyncio.create_task(corpus_sync.run(corpus_sync.keys_to_sync()))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return {"started": True}


from .case_routes import router as _case_router

router.include_router(_case_router)
