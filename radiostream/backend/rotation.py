"""AutoDJ: wählt den nächsten Titel (PLAN-E2.md „Rotation“).

Sperren: gleicher Künstler frühestens nach artist_gap_min, gleicher Titel frühestens nach title_gap_days (aus den
Sender-Einstellungen). Findet sich nichts, wird gelockert – erst die Künstlersperre, dann die Titelsperre –, damit nie
Stille entsteht. Zufällig gewählt; nur Titel im Zustand ok.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from hydrahive.db.connection import db

from . import station

KEEP_DAYS = 30
_SAMPLE = 64            # Kandidaten je Versuch (zufällige Stichprobe statt Volltabelle)


class NothingToPlay(RuntimeError):
    code = "radiostream_library_empty"


def artist_key(artist: str, album_artist: str = "") -> str:
    return " ".join((artist or album_artist or "").lower().split())


def _iso(t: datetime) -> str:
    return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _candidates(conn, rng: random.Random) -> list[dict]:
    """Zufällige Stichprobe über die interne Zeilennummer (rowid). Lücken durch gelöschte Zeilen oder andere Zustände
    werden einfach übersprungen – bei 175.000 Titeln schneller als OFFSET (gemessen 29.10.)."""
    lo, hi = conn.execute("SELECT MIN(rowid), MAX(rowid) FROM module_radiostream_tracks").fetchone()
    if lo is None:
        return []
    if hi - lo < _SAMPLE * 4:
        rows = conn.execute("SELECT track_id, artist, album_artist, title, format FROM module_radiostream_tracks "
                            "WHERE state = 'ok'").fetchall()
    else:
        ids = [rng.randint(lo, hi) for _ in range(_SAMPLE * 2)]
        marks = ",".join("?" * len(ids))
        rows = conn.execute("SELECT track_id, artist, album_artist, title, format FROM module_radiostream_tracks "
                            f"WHERE state = 'ok' AND rowid IN ({marks})", ids).fetchall()
        if not rows:
            rows = conn.execute("SELECT track_id, artist, album_artist, title, format FROM module_radiostream_tracks "
                                "WHERE state = 'ok' LIMIT ?", (_SAMPLE,)).fetchall()
    out = [dict(r) for r in rows]
    rng.shuffle(out)
    return out


def pick(*, now: datetime | None = None, rng: random.Random | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
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
            cands = _candidates(conn, rng)
            if not cands:
                raise NothingToPlay()
            for c in cands:
                if c["track_id"] not in blocked_titles and artist_key(c["artist"], c["album_artist"]) not in blocked_artists:
                    return {**c, "relaxed": False}
        cands = _candidates(conn, rng)
        for c in cands:                                   # Lockern 1: Künstler egal, Titel weiter gesperrt
            if c["track_id"] not in blocked_titles:
                return {**c, "relaxed": True}
        return {**cands[0], "relaxed": True}             # Lockern 2: lieber Wiederholung als Stille


def record(track_id: str, artist: str, *, at: datetime | None = None, album_artist: str = "") -> None:
    with db() as conn:
        conn.execute("INSERT INTO module_radiostream_plays (track_id, artist_key, played_at) VALUES (?, ?, ?)",
                     (track_id, artist_key(artist, album_artist), _iso(at or datetime.now(timezone.utc))))
        conn.commit()


def prune(*, now: datetime | None = None) -> int:
    since = _iso((now or datetime.now(timezone.utc)) - timedelta(days=KEEP_DAYS))
    with db() as conn:
        n = conn.execute("DELETE FROM module_radiostream_plays WHERE played_at < ?", (since,)).rowcount
        conn.commit()
    return n


def recent(limit: int = 10) -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            "SELECT p.track_id, p.played_at, COALESCE(t.artist, '') AS artist, COALESCE(t.title, '') AS title "
            "FROM module_radiostream_plays p LEFT JOIN module_radiostream_tracks t ON t.track_id = p.track_id "
            "ORDER BY p.played_at DESC, p.id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]
