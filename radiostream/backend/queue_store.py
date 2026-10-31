"""Warteschlange „Als Nächstes“ (PLAN-PROGRAMM.md Punkt 5). Hat Vorrang vor Playlist/Mix/Alles."""
from __future__ import annotations

from hydrahive.db.connection import db

from .program_base import MAX_QUEUE, ProgramError, now

_Q = "module_radiostream_queue"


def queue() -> list[dict]:
    with db() as conn:
        rows = conn.execute(f"SELECT q.id, q.pos, q.track_id, q.added_by, COALESCE(t.artist, '') AS artist, "
                            "COALESCE(t.title, '') AS title, t.duration_s FROM "
                            f"{_Q} q LEFT JOIN module_radiostream_tracks t ON t.track_id = q.track_id "
                            "ORDER BY q.pos, q.id").fetchall()
    return [dict(r) for r in rows]


def _renumber(conn, ids: list[int]) -> None:
    conn.executemany(f"UPDATE {_Q} SET pos = ? WHERE id = ?", [(i, qid) for i, qid in enumerate(ids)])


def _ids(conn) -> list[int]:
    return [r[0] for r in conn.execute(f"SELECT id FROM {_Q} ORDER BY pos, id")]


def enqueue(track_id: str, *, user: str, front: bool = False) -> None:
    with db() as conn:
        if not conn.execute("SELECT 1 FROM module_radiostream_tracks WHERE track_id = ? AND state = 'ok'",
                            (track_id,)).fetchone():
            raise ProgramError("radiostream_track_not_found")
        ids = _ids(conn)
        if len(ids) >= MAX_QUEUE:
            raise ProgramError("radiostream_too_many")
        new = conn.execute(f"INSERT INTO {_Q} (pos, track_id, added_by, added_at) VALUES (?, ?, ?, ?)",
                           (len(ids), track_id, user, now())).lastrowid
        _renumber(conn, [new, *ids] if front else [*ids, new])
        conn.commit()


def dequeue(qid: int) -> None:
    with db() as conn:
        conn.execute(f"DELETE FROM {_Q} WHERE id = ?", (qid,))
        _renumber(conn, _ids(conn))
        conn.commit()


def move_queue(qid: int, dst: int) -> None:
    with db() as conn:
        ids = _ids(conn)
        if qid not in ids or not 0 <= dst < len(ids):
            raise ProgramError("radiostream_queue_invalid")
        ids.remove(qid)
        ids.insert(dst, qid)
        _renumber(conn, ids)
        conn.commit()


def pop_first() -> str | None:
    """Ersten Eintrag nehmen und entfernen (Auswahl). None = leer."""
    with db() as conn:
        row = conn.execute(f"SELECT id, track_id FROM {_Q} ORDER BY pos, id LIMIT 1").fetchone()
        if not row:
            return None
        conn.execute(f"DELETE FROM {_Q} WHERE id = ?", (row[0],))
        _renumber(conn, _ids(conn))
        conn.commit()
    return row[1]
