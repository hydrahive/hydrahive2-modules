"""A2 – Routen für den Verlauf ersetzter/verworfener Vorschläge (Spec nichts-geht-verloren.md §2).

Je Szene Text- und Infos-Vorschläge zusammen (neueste zuerst, ohne Text), ein Eintrag mit Text, Zurückholen. Dazu
Gliederung und Steckbriefe (Liste + Zurückholen; die Oberfläche zeigt dort zunächst nur „ersetzt …“).
Lesen: Rolle read. Zurückholen: write (ändert, welcher Vorschlag offen ist – nie das Buch selbst).
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter

from . import _replaced, proposals, proposals_entities, proposals_info, proposals_outline, storage
from ._files import check_id
from ._route_base import Auth, _call, _guard

router = APIRouter()
B = "/projects/{project_id}/books/{book_id}"
S = B + "/scenes/{scene_id}/proposal-history"


def _scene_history(project_id: str, book_id: str, scene_id: str) -> list[dict]:
    storage.get_scene(project_id, book_id, check_id(scene_id, "scene"))   # 404 für unbekannte Szene
    rows = _replaced.history(project_id, book_id, "text", scene_id) + _replaced.history(project_id, book_id, "info", scene_id)
    return sorted(rows, key=lambda r: r["id"], reverse=True)


@router.get(S)
def scene_history(project_id: str, book_id: str, scene_id: str, auth: Auth):
    _guard(auth, project_id, "read")
    return _call(_scene_history, project_id, book_id, scene_id)


@router.get(S + "/{kind}/{entry_id}")
def scene_history_entry(project_id: str, book_id: str, scene_id: str, kind: Literal["text", "info"], entry_id: str,
                        auth: Auth):
    _guard(auth, project_id, "read")
    return _call(_replaced.get, project_id, book_id, kind, scene_id, entry_id)


@router.post(S + "/{kind}/{entry_id}/restore")
def scene_history_restore(project_id: str, book_id: str, scene_id: str, kind: Literal["text", "info"], entry_id: str,
                          auth: Auth):
    _guard(auth, project_id)
    mod = proposals if kind == "text" else proposals_info
    return _call(mod.restore, project_id, book_id, scene_id, entry_id)


def _book_history(project_id: str, book_id: str, kind: str, key: str) -> list[dict]:
    storage.get_book(project_id, book_id)
    return _replaced.history(project_id, book_id, kind, key)


@router.get(B + "/proposal-history/outline")
def outline_history(project_id: str, book_id: str, auth: Auth):
    _guard(auth, project_id, "read")
    return _call(_book_history, project_id, book_id, "outline", "outline")


@router.post(B + "/proposal-history/outline/{entry_id}/restore")
def outline_history_restore(project_id: str, book_id: str, entry_id: str, auth: Auth):
    _guard(auth, project_id)
    return _call(proposals_outline.restore, project_id, book_id, entry_id)


@router.get(B + "/proposal-history/entity/{key}")
def entity_history(project_id: str, book_id: str, key: str, auth: Auth):
    """``key`` = Steckbrief-ID oder „new“ (Vorschläge für neue Steckbriefe)."""
    _guard(auth, project_id, "read")
    return _call(_book_history, project_id, book_id, "entity", key)


@router.post(B + "/proposal-history/entity/{key}/{entry_id}/restore")
def entity_history_restore(project_id: str, book_id: str, key: str, entry_id: str, auth: Auth):
    _guard(auth, project_id)
    return _call(proposals_entities.restore, project_id, book_id, key, entry_id)

