"""Aus einer Idee ein Blueprint-Board machen (Etappe 3a).

Das Blueprint-Modul ist ein eigenes Modul und muss nicht installiert sein. Wie
``task_link.py`` schreibt diese Brücke direkt in dessen Tabelle
``module_blueprint_boards``, aber nur mit dem eigenen Nutzernamen und nur, wenn
es die Tabelle gibt. Board, Verweis an der Idee und Anmerkung entstehen in einer
Transaktion: scheitert ein Schritt, bleibt nichts zurück.

Das Board ist leer und trägt Name und Projekt der Idee. Gezeichnet wird es vom
Nutzer oder vom Agenten (``blueprint_propose``). Der Text der Idee bleibt, wie er ist.
Ab Blueprint 1.3.0 trägt das Board das Projekt; ein älteres Blueprint-Modul ohne
diese Spalte bekommt das Board ohne Projekt.
"""
from __future__ import annotations

import sqlite3

from hydrahive.db.connection import db

from . import notes, store

BOARDS_TABLE = "module_blueprint_boards"
MAX_BOARDS = 200  # wie blueprint/backend/store.py
MAX_NAME = 120  # wie die Routen des Blueprint-Moduls
_IDEAS = "module_scratchpad_ideas"
_EMPTY = '{"nodes":[],"edges":[]}'
_NOW = "strftime('%Y-%m-%dT%H:%M:%SZ','now')"


def _exists(conn: sqlite3.Connection) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (BOARDS_TABLE,)
    ).fetchone() is not None


def _columns(conn: sqlite3.Connection) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({BOARDS_TABLE})")}


def installed() -> bool:
    """Gibt es die Tabelle des Blueprint-Moduls?"""
    with db() as conn:
        return _exists(conn)


def _board(conn: sqlite3.Connection, username: str, board_id: int) -> dict | None:
    """Eigenes Board mit Name und der Angabe, ob ein Vorschlag offen liegt."""
    if not _exists(conn):
        return None
    proposal = "proposal_json IS NOT NULL" if "proposal_json" in _columns(conn) else "0"
    row = conn.execute(
        f'SELECT id, name, {proposal} AS has_proposal FROM {BOARDS_TABLE} WHERE id = ? AND "user" = ?',
        (board_id, username),
    ).fetchone()
    return dict(row) if row else None


def info(username: str, idea: dict) -> dict | None:
    """Verweis für Detailansicht und Agententext. ``None``, wenn die Idee kein Board hat.

    Ein gelöschtes Board, das Board eines anderen Nutzers und ein fehlendes
    Blueprint-Modul sehen gleich aus: ``missing``.
    """
    board_id = idea.get("board_id")
    if board_id is None:
        return None
    with db() as conn:
        board = _board(conn, username, board_id)
    return {
        "id": board_id, "name": board["name"] if board else None,
        "has_proposal": bool(board["has_proposal"]) if board else False, "missing": board is None,
    }


def _insert_board(conn: sqlite3.Connection, username: str, idea: sqlite3.Row) -> int:
    values = {"user": username, "name": idea["title"][:MAX_NAME], "graph_json": _EMPTY}
    if "project_id" in _columns(conn):
        values["project_id"] = idea["project_id"]
    columns = ", ".join(f'"{name}"' for name in values)
    marks = ", ".join("?" for _ in values)
    cursor = conn.execute(
        f"INSERT INTO {BOARDS_TABLE} ({columns}, created_at, updated_at) VALUES ({marks}, {_NOW}, {_NOW})",
        list(values.values()),
    )
    return int(cursor.lastrowid)


def create(username: str, idea_id: str) -> tuple[dict, bool] | None:
    """Board zur Idee anlegen und verknüpfen. Liefert ``(Idee, neu angelegt)``.

    Hat die Idee schon ein Board, kommt dieses zurück und nichts ändert sich.
    ``None`` bei fremder oder unbekannter Idee.
    """
    with db(immediate=True) as conn:
        idea = conn.execute(f"SELECT * FROM {_IDEAS} WHERE username = ? AND id = ?", (username, idea_id)).fetchone()
        if idea is None:
            return None
        if not _exists(conn):
            raise store.IdeaError("blueprint_not_installed")
        # Ein Verweis auf ein gelöschtes oder fremdes Board sperrt nicht: dann entsteht ein neues.
        created = idea["board_id"] is None or _board(conn, username, idea["board_id"]) is None
        if created:
            count = conn.execute(f'SELECT COUNT(*) FROM {BOARDS_TABLE} WHERE "user" = ?', (username,)).fetchone()[0]
            if count >= MAX_BOARDS:
                raise store.IdeaError("boards_full")
            board_id, stamp = _insert_board(conn, username, idea), store.now()
            conn.execute(
                f"UPDATE {_IDEAS} SET board_id = ?, updated_at = ? WHERE username = ? AND id = ?",
                (board_id, stamp, username, idea_id),
            )
            notes.insert(conn, idea_id, author="system", body=f"Board angelegt: ID {board_id}", stamp=stamp)
    return store.get(username, idea_id), created  # type: ignore[return-value]
