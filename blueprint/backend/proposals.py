"""Vorschlag des Agenten neben der Fassung des Nutzers (Etappe 3a).

Ein Board hat die Fassung des Nutzers (``graph_json``) und höchstens einen
offenen Vorschlag (``proposal_json`` mit Notiz und Zeit). Der Agent überschreibt
die Fassung des Nutzers nie: Er legt einen Vorschlag ab, der Nutzer übernimmt
oder verwirft ihn. Nur ein leeres Board wird direkt gezeichnet, weil dort
nichts überschrieben wird.

Den Graphen selbst baut und prüft proposal.py; hier geht es nur ums Speichern.
"""
from __future__ import annotations

import json

from hydrahive.db.connection import db

from . import store, versions

MAX_NOTE = 500
_CLEAR = "proposal_json = NULL, proposal_note = NULL, proposal_at = NULL"
_MINE = 'WHERE "user" = ? AND id = ?'


def _is_empty(graph_json: str) -> bool:
    """Leer ist nur ein lesbares Board ohne Bausteine. Ein unlesbares Board gilt nicht als leer."""
    try:
        graph = json.loads(graph_json)
    except (json.JSONDecodeError, TypeError):
        return False
    return isinstance(graph, dict) and isinstance(graph.get("nodes"), list) and not graph["nodes"]


def put(user: str, board_id: int, graph: dict, note: str = "") -> dict | None:
    """Vorschlag ablegen. Liefert ``{"drawn", "replaced", "board"}`` oder ``None`` bei fremdem Board.

    ``drawn`` ist wahr, wenn das Board leer war und der Vorschlag direkt gezeichnet wurde.
    ``replaced`` ist wahr, wenn dabei ein älterer offener Vorschlag ersetzt wurde.
    """
    raw = json.dumps(graph, ensure_ascii=False)
    with db(immediate=True) as conn:
        board = store.fetch(conn, user, board_id)
        if board is None:
            return None
        drawn = _is_empty(board["graph_json"])
        if drawn:
            conn.execute(
                f"UPDATE {store.TABLE} SET graph_json = ?, {store.BUMP}, {_CLEAR}, updated_at = {store.NOW} {_MINE}",
                (raw, user, board_id),
            )
        else:
            # updated_at bleibt stehen: Die Fassung des Nutzers hat sich nicht geändert.
            conn.execute(
                f"UPDATE {store.TABLE} SET proposal_json = ?, proposal_note = ?, proposal_at = {store.NOW} {_MINE}",
                (raw, (note or "").strip()[:MAX_NOTE], user, board_id),
            )
        replaced = board["proposal_json"] is not None
        return {"drawn": drawn, "replaced": replaced, "board": store.fetch(conn, user, board_id)}


def accept(user: str, board_id: int) -> dict | None:
    """Vorschlag übernehmen: Die bisherige Fassung wandert in die Versionen. ``None`` bei fremdem Board."""
    with db(immediate=True) as conn:
        board = store.fetch(conn, user, board_id)
        if board is None:
            return None
        if board["proposal_json"] is None:
            raise store.BoardError("no_proposal")
        versions.save(conn, board_id, board["graph_json"], "proposal")
        conn.execute(
            f"UPDATE {store.TABLE} SET graph_json = ?, {store.BUMP}, {_CLEAR}, updated_at = {store.NOW} {_MINE}",
            (board["proposal_json"], user, board_id),
        )
        return store.fetch(conn, user, board_id)


def discard(user: str, board_id: int) -> dict | None:
    """Vorschlag verwerfen. Die Fassung des Nutzers bleibt, wie sie ist. ``None`` bei fremdem Board."""
    with db(immediate=True) as conn:
        if not store.owns(conn, user, board_id):
            return None
        conn.execute(f"UPDATE {store.TABLE} SET {_CLEAR} {_MINE}", (user, board_id))
        return store.fetch(conn, user, board_id)
