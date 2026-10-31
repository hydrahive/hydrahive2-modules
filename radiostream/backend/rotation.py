"""AutoDJ: wählt den nächsten Titel (PLAN-E2.md „Rotation“).

Sperren: gleicher Künstler frühestens nach artist_gap_min, gleicher Titel frühestens nach title_gap_days (aus den
Sender-Einstellungen). Findet sich nichts, wird gelockert – erst die Künstlersperre, dann die Titelsperre –, damit nie
Stille entsteht. Zufällig gewählt; nur Titel im Zustand ok.
"""
from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

from hydrahive.db.connection import db

from . import station

KEEP_DAYS = 30
_SAMPLE = 64            # Kandidaten je Versuch (zufällige Stichprobe statt Volltabelle)


class NothingToPlay(RuntimeError):
    code = "radiostream_library_empty"


def artist_key(artist: str, album_artist: str = "") -> str:
    return " ".join((artist or album_artist or "").lower().split())


def _iso(t: datetime) -> str:
    return t.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


_COLS = "t.track_id, t.artist, t.album_artist, t.title, t.format"


def _candidates(conn, rng: random.Random, where: str = "t.state = 'ok'", args: list | None = None) -> list[dict]:
    """Zufällige Stichprobe innerhalb der Bedingung `where` (Programm: Mix-Regel bzw. „Alles“ mit Ausschluss).

    Erst über die interne Zeilennummer (rowid) – bei 175.000 Titeln schneller als OFFSET (gemessen 29.10.). Trifft die
    Stichprobe nichts (enge Regel, z. B. 2 % der Titel), wählt SQLite zufällig aus allen passenden (gemessen 31.10.:
    20–70 ms auf 175.000 Titeln)."""
    args = args or []
    lo, hi = conn.execute("SELECT MIN(rowid), MAX(rowid) FROM module_radiostream_tracks").fetchone()
    if lo is None:
        return []
    rows: list = []
    if hi - lo >= _SAMPLE * 4:
        ids = [rng.randint(lo, hi) for _ in range(_SAMPLE * 2)]
        marks = ",".join("?" * len(ids))
        rows = conn.execute(f"SELECT {_COLS} FROM module_radiostream_tracks t WHERE ({where}) AND t.rowid IN ({marks})",
                            [*args, *ids]).fetchall()
    if len(rows) < 4:
        rows = conn.execute(f"SELECT {_COLS} FROM module_radiostream_tracks t WHERE {where} ORDER BY random() LIMIT ?",
                            [*args, _SAMPLE]).fetchall()
    out = [dict(r) for r in rows]
    rng.shuffle(out)
    return out


def pick(*, now: datetime | None = None, rng: random.Random | None = None, where: str = "t.state = 'ok'",
         args: list | None = None) -> dict:
    """Nächster Titel aus der Bedingung `where` mit den Sperren für Künstler und Titel. Leer → NothingToPlay."""
    now = now or datetime.now(UTC)
    rng = rng or random.Random()
    cfg = station.get()
    artist_since = _iso(now - timedelta(minutes=cfg["artist_gap_min"]))
    title_since = _iso(now - timedelta(days=cfg["title_gap_days"]))
    with db() as conn:
        blocked_artists = {r[0] for r in conn.execute(
            "SELECT DISTINCT artist_key FROM module_radiostream_plays WHERE played_at > ?", (artist_since,))}
        blocked_titles = {r[0] for r in conn.execute(
            "SELECT DISTINCT track_id FROM module_radiostream_plays WHERE played_at > ?", (title_since,))}
        for _ in range(4):
            cands = _candidates(conn, rng, where, args)
            if not cands:
                raise NothingToPlay()
            for c in cands:
                if c["track_id"] not in blocked_titles and artist_key(c["artist"], c["album_artist"]) not in blocked_artists:
                    return {**c, "relaxed": False}
        cands = _candidates(conn, rng, where, args)
        for c in cands:                                   # Lockern 1: Künstler egal, Titel weiter gesperrt
            if c["track_id"] not in blocked_titles:
                return {**c, "relaxed": True}
        return {**cands[0], "relaxed": True}             # Lockern 2: lieber Wiederholung als Stille


def record(track_id: str, artist: str, *, at: datetime | None = None, album_artist: str = "", source: str = "",
           ref: str = "") -> int:
    """In die Gespielt-Liste (Sperren, „zuletzt gespielt“). source/ref = Herkunft, für das Zurücknehmen (preload.py)."""
    with db() as conn:
        pid = conn.execute("INSERT INTO module_radiostream_plays (track_id, artist_key, played_at, source, ref) "
                           "VALUES (?, ?, ?, ?, ?)", (track_id, artist_key(artist, album_artist),
                                                      _iso(at or datetime.now(UTC)), source, ref)).lastrowid
        conn.commit()
    return int(pid)


def play_origin(play_id: int) -> dict | None:
    with db() as conn:
        r = conn.execute("SELECT track_id, source, ref FROM module_radiostream_plays WHERE id = ?", (play_id,)).fetchone()
    return dict(r) if r else None


def unrecord(play_id: int) -> None:
    with db() as conn:
        conn.execute("DELETE FROM module_radiostream_plays WHERE id = ?", (play_id,))
        conn.commit()


def prune(*, now: datetime | None = None) -> int:
    since = _iso((now or datetime.now(UTC)) - timedelta(days=KEEP_DAYS))
    with db() as conn:
        n = conn.execute("DELETE FROM module_radiostream_plays WHERE played_at < ?", (since,)).rowcount
        conn.commit()
    return n


def recent(limit: int = 10) -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            "SELECT p.id AS play_id, p.track_id, p.played_at, COALESCE(t.artist, '') AS artist, "
            "COALESCE(t.title, '') AS title "
            "FROM module_radiostream_plays p LEFT JOIN module_radiostream_tracks t ON t.track_id = p.track_id "
            "ORDER BY p.played_at DESC, p.id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]
