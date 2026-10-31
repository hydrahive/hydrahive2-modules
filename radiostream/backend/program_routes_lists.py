"""Schnittstellen Playlisten und Mixe (PLAN-PROGRAMM.md). Rechte und Ablauf wie program_routes.py."""
from __future__ import annotations

from fastapi import APIRouter, status
from hydrahive.api.middleware.errors import coded

from . import mixes, playlists, search
from .program_models import (
    ItemsIn,
    MixIn,
    MoveIn,
    NameIn,
    PlaylistIn,
    PreviewIn,
    SearchIn,
)
from .program_routes import Moderator, Principal, _do

router = APIRouter()


# --- Playlisten --------------------------------------------------------------------------------------------------------

@router.get("/playlists")
def list_playlists(p: Principal):
    return {"items": playlists.playlists()}


@router.post("/playlists", status_code=status.HTTP_201_CREATED)
def create_playlist(p: Moderator, body: NameIn):
    return _do(lambda: playlists.create_playlist(body.name, user=p.username), change=False)


@router.get("/playlists/{pid}")
def get_playlist(p: Principal, pid: str):
    pl = next((x for x in playlists.playlists() if x["id"] == pid), None)
    if pl is None:
        raise coded(404, "radiostream_playlist_not_found")
    return {**pl, "items": playlists.items(pid)}


@router.put("/playlists/{pid}")
def update_playlist(p: Moderator, pid: str, body: PlaylistIn):
    return _do(lambda: playlists.update_playlist(pid, name=body.name, order_mode=body.order_mode, at_end=body.at_end))


@router.delete("/playlists/{pid}")
def delete_playlist(p: Moderator, pid: str):
    _do(lambda: playlists.delete_playlist(pid))
    return {"ok": True}


@router.post("/playlists/{pid}/items")
def add_items(p: Moderator, pid: str, body: ItemsIn):
    return {"added": _do(lambda: playlists.add_items(pid, body.track_ids))}


@router.post("/playlists/{pid}/add-search")
def add_search(p: Moderator, pid: str, body: SearchIn):
    """„Alle Treffer hinzufügen“ – dieselbe Suche wie die Bibliothek, höchstens 500 Titel."""
    hits = search.tracks(q=body.q, artist=body.artist, genre=body.genre, fmt=body.format, year_from=body.year_from,
                         year_to=body.year_to, limit=500)["items"]
    return {"added": _do(lambda: playlists.add_items(pid, [h["track_id"] for h in hits]))}


@router.post("/playlists/{pid}/move")
def move_item(p: Moderator, pid: str, body: MoveIn):
    _do(lambda: playlists.move_item(pid, body.from_, body.to))
    return {"ok": True}


@router.delete("/playlists/{pid}/items/{pos}")
def remove_item(p: Moderator, pid: str, pos: int):
    _do(lambda: playlists.remove_item(pid, pos))
    return {"ok": True}


# --- Mixe --------------------------------------------------------------------------------------------------------------

@router.get("/mixes")
def list_mixes(p: Principal):
    return {"items": mixes.mixes()}


@router.post("/mixes/preview")
def preview(p: Principal, body: PreviewIn):
    return _do(lambda: mixes.preview(body.rules, allow_long=body.allow_long), change=False)


@router.post("/mixes", status_code=status.HTTP_201_CREATED)
def create_mix(p: Moderator, body: MixIn):
    return _do(lambda: mixes.save_mix(None, name=body.name, rules_=body.rules, allow_long=body.allow_long,
                                      user=p.username), change=False)


@router.put("/mixes/{mid}")
def update_mix(p: Moderator, mid: str, body: MixIn):
    return _do(lambda: mixes.save_mix(mid, name=body.name, rules_=body.rules, allow_long=body.allow_long,
                                      user=p.username))


@router.delete("/mixes/{mid}")
def delete_mix(p: Moderator, mid: str):
    _do(lambda: mixes.delete_mix(mid))
    return {"ok": True}


