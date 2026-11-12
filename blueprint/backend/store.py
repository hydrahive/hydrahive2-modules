"""Blueprint-Store — Boards pro User, ownership-strikt.

Jede Zeile gehört dem anlegenden User; alle Ops filtern auf "user". Fremde
Boards sind unsichtbar und unveränderbar. Hartes Limit gegen Missbrauch.
graph_json wird als roher String gespeichert (validiertes JSON kommt aus der
Route).

Seit 1.3.0 kann ein Board einem Projekt zugeordnet sein und höchstens einen
offenen Vorschlag des Agenten tragen (proposals.py). Der Vorschlag liegt neben
der Fassung des Nutzers und ändert graph_json nicht.
"""
from __future__ import annotations

import sqlite3

from hydrahive.db.connection import db

TABLE = "module_blueprint_boards"
NOW = "strftime('%Y-%m-%dT%H:%M:%SZ','now')"
EMPTY = '{"nodes":[],"edges":[]}'
_MAX = 200
_UNSET = object()
_META = "id, name, project_id, created_at, updated_at"
_FULL = f"{_META}, graph_json, proposal_json, proposal_note, proposal_at"


class BoardError(ValueError):
    """Fachlicher Fehler mit Code, zum Beispiel ``boards_full`` oder ``no_proposal``."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def list_for(user: str, project_id: str | None = None) -> list[dict]:
    """Boards des Users (ohne graph_json — nur Metadaten für die Liste), auf Wunsch nur eines Projekts."""
    where, args = '"user" = ?', [user]
    if project_id:
        where += " AND project_id = ?"
        args.append(project_id)
    with db() as c:
        rows = c.execute(
            f"SELECT {_META}, proposal_json IS NOT NULL AS has_proposal FROM {TABLE} "
            f"WHERE {where} ORDER BY updated_at DESC, id DESC",
            args,
        ).fetchall()
    return [{**dict(row), "has_proposal": bool(row["has_proposal"])} for row in rows]


def owns(conn: sqlite3.Connection, user: str, board_id: int) -> bool:
    return conn.execute(f'SELECT 1 FROM {TABLE} WHERE "user" = ? AND id = ?', (user, board_id)).fetchone() is not None


def fetch(conn: sqlite3.Connection, user: str, board_id: int) -> dict | None:
    """Vollständiges Board innerhalb einer laufenden Transaktion."""
    row = conn.execute(f'SELECT {_FULL} FROM {TABLE} WHERE "user" = ? AND id = ?', (user, board_id)).fetchone()
    return dict(row) if row else None


def get(user: str, board_id: int) -> dict | None:
    """Ein vollständiges Board (inkl. graph_json und offenem Vorschlag) des Users."""
    with db() as c:
        return fetch(c, user, board_id)


def create(user: str, name: str, project_id: str | None = None) -> dict:
    with db() as c:
        count = c.execute(f'SELECT COUNT(*) FROM {TABLE} WHERE "user" = ?', (user,)).fetchone()[0]
        if count >= _MAX:
            raise BoardError("boards_full")
        cur = c.execute(
            f'INSERT INTO {TABLE} ("user", name, project_id, graph_json, created_at, updated_at) '
            f"VALUES (?, ?, ?, ?, {NOW}, {NOW})",
            (user, name, project_id, EMPTY),
        )
        bid = cur.lastrowid
    return get(user, bid)  # type: ignore[return-value]


def update(user: str, board_id: int, *, name: str | None = None, graph_json: str | None = None,
           project_id: str | None | object = _UNSET) -> dict | None:
    """Name, Graph und/oder Projekt aktualisieren. Nur eigene Boards.

    ``project_id=None`` löst das Board vom Projekt; ohne Angabe bleibt das Projekt, wie es ist.
    """
    sets: list[str] = []
    args: list = []
    if name is not None:
        sets.append("name = ?")
        args.append(name)
    if graph_json is not None:
        sets.append("graph_json = ?")
        args.append(graph_json)
    if project_id is not _UNSET:
        sets.append("project_id = ?")
        args.append(project_id)
    if not sets:
        return get(user, board_id)
    sets.append(f"updated_at = {NOW}")
    args.extend([user, board_id])
    with db() as c:
        cur = c.execute(f'UPDATE {TABLE} SET {", ".join(sets)} WHERE "user" = ? AND id = ?', tuple(args))
        if cur.rowcount == 0:
            return None
    return get(user, board_id)


def remove(user: str, board_id: int) -> bool:
    """Board löschen. Die früheren Fassungen (versions.py) gehen über den Fremdschlüssel mit."""
    with db() as c:
        cur = c.execute(f'DELETE FROM {TABLE} WHERE "user" = ? AND id = ?', (user, board_id))
        return cur.rowcount > 0
