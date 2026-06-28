"""Blueprint-Store — Boards pro User, ownership-strikt.

Jede Zeile gehört dem anlegenden User; alle Ops filtern auf "user". Fremde
Boards sind unsichtbar und unveränderbar. Hartes Limit gegen Missbrauch.
graph_json wird als roher String gespeichert (validiertes JSON kommt aus der
Route).
"""
from __future__ import annotations

from hydrahive.db.connection import db

_NOW = "strftime('%Y-%m-%dT%H:%M:%SZ','now')"
_MAX = 200
_EMPTY = '{"nodes":[],"edges":[]}'


def list_for(user: str) -> list[dict]:
    """Boards des Users (ohne graph_json — nur Metadaten für die Liste)."""
    with db() as c:
        return [
            dict(r)
            for r in c.execute(
                'SELECT id, name, created_at, updated_at '
                'FROM module_blueprint_boards WHERE "user" = ? '
                "ORDER BY updated_at DESC, id DESC",
                (user,),
            ).fetchall()
        ]


def get(user: str, board_id: int) -> dict | None:
    """Ein vollständiges Board (inkl. graph_json) des Users."""
    with db() as c:
        row = c.execute(
            'SELECT id, name, graph_json, created_at, updated_at '
            'FROM module_blueprint_boards WHERE "user" = ? AND id = ?',
            (user, board_id),
        ).fetchone()
        return dict(row) if row else None


def create(user: str, name: str) -> dict:
    with db() as c:
        count = c.execute(
            'SELECT COUNT(*) FROM module_blueprint_boards WHERE "user" = ?',
            (user,),
        ).fetchone()[0]
        if count >= _MAX:
            raise ValueError("boards_full")
        cur = c.execute(
            'INSERT INTO module_blueprint_boards ("user", name, graph_json, created_at, updated_at) '
            f"VALUES (?, ?, ?, {_NOW}, {_NOW})",
            (user, name, _EMPTY),
        )
        bid = cur.lastrowid
    return get(user, bid)  # type: ignore[return-value]


def update(user: str, board_id: int, *, name: str | None = None,
           graph_json: str | None = None) -> dict | None:
    """Name und/oder Graph aktualisieren. Nur eigene Boards."""
    sets: list[str] = []
    args: list = []
    if name is not None:
        sets.append("name = ?")
        args.append(name)
    if graph_json is not None:
        sets.append("graph_json = ?")
        args.append(graph_json)
    if not sets:
        return get(user, board_id)
    sets.append(f"updated_at = {_NOW}")
    args.extend([user, board_id])
    with db() as c:
        cur = c.execute(
            f'UPDATE module_blueprint_boards SET {", ".join(sets)} '
            'WHERE "user" = ? AND id = ?',
            tuple(args),
        )
        if cur.rowcount == 0:
            return None
    return get(user, board_id)


def remove(user: str, board_id: int) -> bool:
    with db() as c:
        cur = c.execute(
            'DELETE FROM module_blueprint_boards WHERE "user" = ? AND id = ?',
            (user, board_id),
        )
        return cur.rowcount > 0
