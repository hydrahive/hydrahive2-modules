"""Auswahl des nächsten Titels (PLAN-PROGRAMM.md „Auswahl“): Warteschlange → Playlist/Mix → Alles.

- Warteschlange: ohne Sperren, verbraucht den Eintrag. Titel inzwischen weg → nächster Eintrag.
- Playlist: der Reihe nach (Stelle merken) oder gemischt (jede Stelle einmal je Runde). Sperren gelten nicht.
  Am Ende von vorn oder zurück zu „Alles“ (Programm wird dann auf „Alles“ gestellt).
- Mix: zufällig aus der Regel, mit Sperren (gelockert statt Stille). „Ausgeschlossen von Alles“ gilt hier nicht.
- Alles: zufällig mit Ausschluss (Hörbücher …) und Sperren.
- Nie Stille: leere Playlist/leerer Mix → Alles + Hinweis `radiostream_program_empty` (Wahl bleibt stehen). Nichts mehr
  übrig in „Alles“ → Ausschluss ignorieren (relaxed). Erst eine leere Bibliothek ergibt NothingToPlay.
"""
from __future__ import annotations

import random
from datetime import UTC, datetime

from hydrahive.db.connection import db

from . import mixes, playlists, program, queue_store, rotation, rules

EMPTY = "radiostream_program_empty"


class _BackToAll(Exception):
    """Playlist ist durch und soll danach zu „Alles“ zurück (at_end = back)."""


def _track(track_id: str) -> dict | None:
    with db() as conn:
        r = conn.execute("SELECT track_id, artist, album_artist, title, format FROM module_radiostream_tracks "
                         "WHERE track_id = ? AND state = 'ok'", (track_id,)).fetchone()
    return dict(r) if r else None


def _from_queue() -> dict | None:
    while (tid := queue_store.pop_first()) is not None:
        if t := _track(tid):
            return {**t, "relaxed": False, "source": "queue", "ref": ""}
    return None


def _from_playlist(pid: str, prog: dict, rng: random.Random) -> dict | None:
    with db() as conn:
        pl = conn.execute("SELECT order_mode, at_end FROM module_radiostream_playlists WHERE id = ?", (pid,)).fetchone()
    entries = playlists.items(pid)
    avail = [e for e in entries if e["available"]]
    if not pl or not avail:
        return None
    if pl["order_mode"] == "shuffle":
        played = [p for p in prog["played"] if p < len(entries)]
        left = [e for e in avail if e["pos"] not in played]
        if not left:
            if pl["at_end"] == "back":
                raise _BackToAll()
            played, left = [], avail
        e = rng.choice(left)
        program.save_position(played=[*played, e["pos"]])
        mode = "shuffle"
    else:
        later = [x for x in avail if x["pos"] >= prog["cursor"]]
        if not later:
            if pl["at_end"] == "back":
                raise _BackToAll()
            later = avail
        e = later[0]
        program.save_position(cursor=e["pos"] + 1)
        mode = "ordered"
    t = _track(e["track_id"])
    return {**t, "relaxed": False, "source": "playlist", "ref": f"{pid}:{mode}:{e['pos']}"} if t else None


def _from_mix(mid: str, now: datetime, rng: random.Random) -> dict | None:
    m = mixes.mix(mid)
    if not m:
        return None
    where, args = rules.where(m["rules"], exclude={}, allow_long=m["allow_long"])
    try:
        return {**rotation.pick(now=now, rng=rng, where=where, args=args), "source": "mix", "ref": mid}
    except rotation.NothingToPlay:
        return None


def _from_all(now: datetime, rng: random.Random) -> dict:
    ex = mixes.get_exclude()
    where, args = rules.where({}, exclude=ex["rules"], allow_long=ex["allow_long"])
    try:
        return {**rotation.pick(now=now, rng=rng, where=where, args=args), "source": "all", "ref": ""}
    except rotation.NothingToPlay:
        t = rotation.pick(now=now, rng=rng)                  # lieber Ausgeschlossenes als Stille
        return {**t, "relaxed": True, "source": "all", "ref": ""}


def next_track(*, now: datetime | None = None, rng: random.Random | None = None) -> dict:
    """Nächster Titel als dict (track_id, artist, album_artist, title, format, relaxed, source, ref)."""
    now = now or datetime.now(UTC)
    rng = rng or random.Random()
    if t := _from_queue():
        return t
    prog = program.get_program()
    got = None
    if prog["mode"] == "playlist":
        try:
            got = _from_playlist(prog["ref_id"], prog, rng)
        except _BackToAll:
            program.set_program("all", "", user="system")
            return _from_all(now, rng)
    elif prog["mode"] == "mix":
        got = _from_mix(prog["ref_id"], now, rng)
    if prog["mode"] != "all":
        program.save_position(notice="" if got else EMPTY)
    return got or _from_all(now, rng)
