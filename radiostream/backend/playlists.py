"""Playlisten (PLAN-PROGRAMM.md „Playlisten“): anlegen, ändern, Titel hinzufügen/umsortieren/entfernen."""
from __future__ import annotations

from hydrahive.db.connection import db

from .program_base import MAX_ADD, MAX_ITEMS, ProgramError, clean_name, new_id, now

_T = "module_radiostream_playlists"
_I = "module_radiostream_playlist_items"
ORDER = ("ordered", "shuffle")
AT_END = ("repeat", "back")


def _get(conn, pid: str) -> dict:
    row = conn.execute(f"SELECT p.*, (SELECT COUNT(*) FROM {_I} i WHERE i.playlist_id = p.id) AS count FROM {_T} p "
                       "WHERE p.id = ?", (pid,)).fetchone()
    if not row:
        raise ProgramError("radiostream_playlist_not_found")
    return dict(row)


def playlists() -> list[dict]:
    with db() as conn:
        rows = conn.execute(f"SELECT p.*, (SELECT COUNT(*) FROM {_I} i WHERE i.playlist_id = p.id) AS count "
                            f"FROM {_T} p ORDER BY lower(p.name), p.id").fetchall()
    return [dict(r) for r in rows]


def create_playlist(name: str, *, user: str) -> dict:
    pid = new_id()
    with db() as conn:
        conn.execute(f"INSERT INTO {_T} (id, name, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                     (pid, clean_name(name), user, now(), now()))
        conn.commit()
        return _get(conn, pid)


def update_playlist(pid: str, *, name: str | None = None, order_mode: str | None = None,
                    at_end: str | None = None) -> dict:
    if (order_mode is not None and order_mode not in ORDER) or (at_end is not None and at_end not in AT_END):
        raise ProgramError("radiostream_playlist_invalid")
    with db() as conn:
        cur = _get(conn, pid)
        conn.execute(f"UPDATE {_T} SET name = ?, order_mode = ?, at_end = ?, updated_at = ? WHERE id = ?",
                     (clean_name(name) if name is not None else cur["name"], order_mode or cur["order_mode"],
                      at_end or cur["at_end"], now(), pid))
        conn.commit()
        return _get(conn, pid)


def delete_playlist(pid: str) -> None:
    from .program import reset_if_points_to
    with db() as conn:
        conn.execute(f"DELETE FROM {_I} WHERE playlist_id = ?", (pid,))
        conn.execute(f"DELETE FROM {_T} WHERE id = ?", (pid,))
        conn.commit()
    reset_if_points_to("playlist", pid)


def items(pid: str) -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            f"SELECT i.pos, i.track_id, COALESCE(t.artist, '') AS artist, COALESCE(t.title, '') AS title, "
            "t.duration_s, COALESCE(t.state = 'ok', 0) AS available FROM "
            f"{_I} i LEFT JOIN module_radiostream_tracks t ON t.track_id = i.track_id WHERE i.playlist_id = ? "
            "ORDER BY i.pos", (pid,)).fetchall()
    return [{**dict(r), "available": bool(r["available"])} for r in rows]


def _renumber(conn, pid: str, order: list[str]) -> None:
    conn.execute(f"DELETE FROM {_I} WHERE playlist_id = ?", (pid,))
    conn.executemany(f"INSERT INTO {_I} (playlist_id, pos, track_id) VALUES (?, ?, ?)",
                     [(pid, i, t) for i, t in enumerate(order)])
    conn.execute(f"UPDATE {_T} SET updated_at = ? WHERE id = ?", (now(), pid))


def add_items(pid: str, track_ids: list[str]) -> int:
    """Hängt bekannte Titel ans Ende. Unbekannte werden übergangen. Doppelte sind erlaubt."""
    if len(track_ids) > MAX_ADD:
        raise ProgramError("radiostream_too_many")
    with db() as conn:
        cur = _get(conn, pid)
        marks = ",".join("?" * len(track_ids)) or "''"
        known = {r[0] for r in conn.execute(f"SELECT track_id FROM module_radiostream_tracks WHERE track_id IN "
                                            f"({marks})", track_ids)}
        add = [t for t in track_ids if t in known]
        if cur["count"] + len(add) > MAX_ITEMS:
            raise ProgramError("radiostream_too_many")
        conn.executemany(f"INSERT INTO {_I} (playlist_id, pos, track_id) VALUES (?, ?, ?)",
                         [(pid, cur["count"] + i, t) for i, t in enumerate(add)])
        conn.execute(f"UPDATE {_T} SET updated_at = ? WHERE id = ?", (now(), pid))
        conn.commit()
    return len(add)


def move_item(pid: str, src: int, dst: int) -> None:
    with db() as conn:
        _get(conn, pid)
        order = [r[0] for r in conn.execute(f"SELECT track_id FROM {_I} WHERE playlist_id = ? ORDER BY pos", (pid,))]
        if not (0 <= src < len(order) and 0 <= dst < len(order)):
            raise ProgramError("radiostream_playlist_invalid")
        order.insert(dst, order.pop(src))
        _renumber(conn, pid, order)
        conn.commit()


def remove_item(pid: str, pos: int) -> None:
    with db() as conn:
        _get(conn, pid)
        order = [r[0] for r in conn.execute(f"SELECT track_id FROM {_I} WHERE playlist_id = ? ORDER BY pos", (pid,))]
        if not 0 <= pos < len(order):
            raise ProgramError("radiostream_playlist_invalid")
        order.pop(pos)
        _renumber(conn, pid, order)
        conn.commit()
