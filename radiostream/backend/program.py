"""Programm (PLAN-PROGRAMM.md): gemeinsame Teile + Programmwahl. Playlisten in playlists.py, Mixe/Ausschluss in
mixes.py, Warteschlange in queue_store.py – hier wieder eingesammelt, damit Routen und Auswahl einen Ort haben."""
from __future__ import annotations

import json

from hydrahive.db.connection import db

from .mixes import (  # noqa: F401
    delete_mix,
    folder_suggestions,
    get_exclude,
    mixes,
    preview,
    save_exclude,
    save_mix,
)
from .playlists import (  # noqa: F401
    add_items,
    create_playlist,
    delete_playlist,
    items,
    move_item,
    playlists,
    remove_item,
    update_playlist,
)
from .program_base import MAX_ITEMS, MAX_QUEUE, ProgramError, now  # noqa: F401
from .queue_store import dequeue, enqueue, move_queue, queue  # noqa: F401

MODES = ("all", "playlist", "mix")


def get_program() -> dict:
    with db() as conn:
        row = conn.execute("SELECT mode, ref_id, cursor, played, notice FROM module_radiostream_program "
                           "WHERE id = 1").fetchone()
    if not row:
        return {"mode": "all", "ref_id": "", "cursor": 0, "played": [], "notice": ""}
    return {**dict(row), "played": json.loads(row["played"] or "[]")}


def _exists(table: str, ref_id: str) -> bool:
    with db() as conn:
        return conn.execute(f"SELECT 1 FROM {table} WHERE id = ?", (ref_id,)).fetchone() is not None


def set_program(mode: str, ref_id: str, *, user: str) -> dict:
    """Programm wählen. Stelle der Playlist und „schon gespielt“ beginnen neu."""
    if mode not in MODES:
        raise ProgramError("radiostream_program_invalid")
    if mode == "all":
        ref_id = ""
    elif not _exists("module_radiostream_playlists" if mode == "playlist" else "module_radiostream_mixes", ref_id):
        raise ProgramError("radiostream_playlist_not_found" if mode == "playlist" else "radiostream_mix_not_found")
    with db() as conn:
        conn.execute("INSERT INTO module_radiostream_program (id, mode, ref_id, cursor, played, notice, updated_by, "
                     "updated_at) VALUES (1, ?, ?, 0, '[]', '', ?, ?) ON CONFLICT(id) DO UPDATE SET mode = "
                     "excluded.mode, ref_id = excluded.ref_id, cursor = 0, played = '[]', notice = '', "
                     "updated_by = excluded.updated_by, updated_at = excluded.updated_at", (mode, ref_id, user, now()))
        conn.commit()
    return get_program()


def save_position(*, cursor: int | None = None, played: list[int] | None = None, notice: str | None = None) -> None:
    """Fortschritt der Playlist / Hinweis (z. B. „Playlist leer, es läuft Alles“) – nur von der Auswahl benutzt."""
    sets, args = [], []
    for col, val in (("cursor", cursor), ("played", None if played is None else json.dumps(played)),
                     ("notice", notice)):
        if val is not None:
            sets.append(f"{col} = ?")
            args.append(val)
    if not sets:
        return
    with db() as conn:
        conn.execute("INSERT OR IGNORE INTO module_radiostream_program (id) VALUES (1)")
        conn.execute(f"UPDATE module_radiostream_program SET {', '.join(sets)} WHERE id = 1", args)
        conn.commit()


def reset_if_points_to(mode: str, ref_id: str) -> None:
    if get_program()["mode"] == mode and get_program()["ref_id"] == ref_id:
        set_program("all", "", user="system")
