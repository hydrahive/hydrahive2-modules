"""Schnittstellen „Programm“ (PLAN-PROGRAMM.md). Lesen: jeder mit Modul-Freigabe (Modul-Tor des Kerns). Ändern:
radiostream.moderate (Entscheidung B, 31.10.). „Ausgeschlossen von Alles“: radiostream.control (Sender-Einstellung).

Jede Änderung, die das Gesendete betrifft, läuft durch preload.changing(): erst den vorgeladenen Titel zurücknehmen,
dann ändern – sonst käme „Als Nächstes“ erst einen Titel später. Playlisten und Mixe: program_routes_lists.py."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from hydrahive.access import check
from hydrahive.access.deps import require_capability
from hydrahive.api.middleware.auth import AuthPrincipal, require_principal
from hydrahive.api.middleware.errors import coded

from . import mixes, playlists, preload, program
from .program_base import ProgramError
from .program_models import ExcludeIn, PosIn, ProgramIn, QueueIn

MODERATE = "radiostream.moderate"
CONTROL = "radiostream.control"
router = APIRouter()
Principal = Annotated[AuthPrincipal, Depends(require_principal)]
Moderator = Annotated[AuthPrincipal, Depends(require_capability(MODERATE))]
Controller = Annotated[AuthPrincipal, Depends(require_capability(CONTROL))]
_HTTP = {"radiostream_playlist_not_found": 404, "radiostream_mix_not_found": 404, "radiostream_track_not_found": 404}


def _do(fn, *, change: bool = True):
    try:
        if not change:
            return fn()
        with preload.changing():
            return fn()
    except ProgramError as e:
        raise coded(_HTTP.get(e.code, status.HTTP_400_BAD_REQUEST), e.code) from None


# --- Programm ----------------------------------------------------------------------------------------------------------

@router.get("/program")
def get_program(p: Principal):
    prog = program.get_program()
    out = {**{k: prog[k] for k in ("mode", "ref_id", "notice")}, "name": "", "count": 0, "position": 0,
           "can_moderate": check.can_use(user_id=p.user_id, role=p.role, capability=MODERATE)}
    if prog["mode"] == "playlist":
        pl = next((x for x in playlists.playlists() if x["id"] == prog["ref_id"]), None)
        if pl:
            out.update(name=pl["name"], count=pl["count"],
                       position=len(prog["played"]) if pl["order_mode"] == "shuffle" else prog["cursor"])
    elif prog["mode"] == "mix" and (m := mixes.mix(prog["ref_id"])):
        out.update(name=m["name"], count=mixes.preview(m["rules"], allow_long=m["allow_long"])["count"])
    return out


@router.put("/program")
def put_program(p: Moderator, body: ProgramIn):
    _do(lambda: program.set_program(body.mode, body.ref_id, user=p.username))
    return get_program(p)


# --- Warteschlange -----------------------------------------------------------------------------------------------------

@router.get("/queue")
def list_queue(p: Principal):
    return {"items": program.queue()}


@router.post("/queue")
def enqueue(p: Moderator, body: QueueIn):
    _do(lambda: program.enqueue(body.track_id, user=p.username, front=body.front))
    return {"items": program.queue()}


@router.put("/queue/{qid}")
def move_queue(p: Moderator, qid: int, body: PosIn):
    _do(lambda: program.move_queue(qid, body.pos))
    return {"items": program.queue()}


@router.delete("/queue/{qid}")
def dequeue(p: Moderator, qid: int):
    _do(lambda: program.dequeue(qid))
    return {"items": program.queue()}


# --- Ausgeschlossen von Alles ------------------------------------------------------------------------------------------

@router.get("/exclude")
def get_exclude(p: Principal):
    return {**mixes.get_exclude(), "suggestions": mixes.folder_suggestions()}


@router.put("/exclude")
def put_exclude(p: Controller, body: ExcludeIn):
    return _do(lambda: mixes.save_exclude(body.rules, allow_long=body.allow_long, user=p.username))
