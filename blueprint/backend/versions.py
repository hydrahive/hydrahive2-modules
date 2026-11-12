"""Frühere Fassungen eines Boards (Etappe 3a).

Bevor ein Vorschlag des Agenten die Fassung des Nutzers ersetzt, wandert die
bisherige Fassung hierher und lässt sich wiederherstellen. Je Board bleiben die
letzten ``KEEP`` Fassungen. Auch das Wiederherstellen sichert vorher den
aktuellen Stand, damit nichts verloren geht.
"""
from __future__ import annotations

import sqlite3

from hydrahive.db.connection import db

from . import store

TABLE = "module_blueprint_versions"
KEEP = 20


def save(conn: sqlite3.Connection, board_id: int, graph_json: str, source: str) -> None:
    """Fassung innerhalb einer laufenden Transaktion sichern und auf ``KEEP`` Fassungen kürzen.

    ``source``: ``proposal`` (vor dem Übernehmen eines Vorschlags) oder ``restore`` (vor dem Wiederherstellen).
    """
    conn.execute(
        f"INSERT INTO {TABLE} (board_id, graph_json, node_count, source, created_at) "
        f"VALUES (?, ?, ?, ?, {store.NOW})",
        (board_id, graph_json, store.node_count(graph_json), source),
    )
    conn.execute(
        f"DELETE FROM {TABLE} WHERE board_id = ? AND id NOT IN "
        f"(SELECT id FROM {TABLE} WHERE board_id = ? ORDER BY id DESC LIMIT ?)",
        (board_id, board_id, KEEP),
    )


def list_for(user: str, board_id: int) -> list[dict] | None:
    """Frühere Fassungen, neueste zuerst, ohne den Graphen. ``None`` bei fremdem oder unbekanntem Board."""
    with db() as conn:
        if not store.owns(conn, user, board_id):
            return None
        rows = conn.execute(
            f"SELECT id, source, node_count, created_at FROM {TABLE} WHERE board_id = ? ORDER BY id DESC",
            (board_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def restore(user: str, board_id: int, version_id: int) -> dict | None:
    """Frühere Fassung wieder zur Fassung des Nutzers machen.

    ``None`` bei fremdem Board oder wenn die Fassung nicht zu diesem Board gehört.
    Ein offener Vorschlag bleibt liegen.
    """
    with db(immediate=True) as conn:
        board = store.fetch(conn, user, board_id)
        if board is None:
            return None
        row = conn.execute(
            f"SELECT graph_json FROM {TABLE} WHERE id = ? AND board_id = ?", (version_id, board_id)
        ).fetchone()
        if row is None:
            return None
        save(conn, board_id, board["graph_json"], "restore")
        conn.execute(
            f'UPDATE {store.TABLE} SET graph_json = ?, updated_at = {store.NOW} WHERE "user" = ? AND id = ?',
            (row["graph_json"], user, board_id),
        )
        return store.fetch(conn, user, board_id)
