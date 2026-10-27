"""Suche und Statistik über die Bibliothek (FTS5, Cursor-Blättern). SPEC „Schnittstellen“."""
from __future__ import annotations

import base64
import json
import re

from hydrahive.db.connection import db

PUBLIC = ("track_id", "artist", "album_artist", "title", "album", "genre", "year", "track_no", "duration_s",
          "bitrate", "sample_rate", "format", "state")
_WORD = re.compile(r"\w+", re.UNICODE)
_ORDER = ("artist", "album", "track_no", "title", "track_id")


def _fts_query(q: str) -> str | None:
    """Nutzereingabe → sichere FTS5-Abfrage: jedes Wort als Präfix, alles UND-verknüpft, keine Operatoren."""
    words = _WORD.findall(q or "")
    return " ".join(f'"{w}"*' for w in words) or None


def _enc(row: dict) -> str:
    key = [row["artist"].lower(), row["album"].lower(), row["track_no"] or 0, row["title"].lower(), row["track_id"]]
    return base64.urlsafe_b64encode(json.dumps(key).encode()).decode()


def _dec(cursor: str) -> list:
    try:
        key = json.loads(base64.urlsafe_b64decode(cursor.encode()))
        if isinstance(key, list) and len(key) == 5:
            return key
    except (ValueError, TypeError):
        pass
    return []


def tracks(*, q: str = "", artist: str = "", genre: str = "", fmt: str = "", year_from: int | None = None,
           year_to: int | None = None, state: str = "ok", limit: int = 100, cursor: str = "") -> dict:
    where, args = ["t.state = ?"], [state]
    join = ""
    fts = _fts_query(q)
    if fts:
        join = "JOIN module_radiostream_tracks_fts f ON f.rowid = t.rowid"
        where.append("module_radiostream_tracks_fts MATCH ?")
        args.append(fts)
    for col, val in (("t.artist", artist), ("t.genre", genre), ("t.format", fmt.lower())):
        if val:
            where.append(f"{col} = ? COLLATE NOCASE")
            args.append(val)
    if year_from is not None:
        where.append("t.year >= ?")
        args.append(year_from)
    if year_to is not None:
        where.append("t.year <= ?")
        args.append(year_to)
    key = _dec(cursor) if cursor else []
    if key:
        where.append("(lower(t.artist), lower(t.album), COALESCE(t.track_no, 0), lower(t.title), t.track_id) > "
                     "(?, ?, ?, ?, ?)")
        args.extend(key)
    cols = ", ".join(f"t.{c}" for c in PUBLIC)
    sql = (f"SELECT {cols} FROM module_radiostream_tracks t {join} WHERE {' AND '.join(where)} "
           "ORDER BY lower(t.artist), lower(t.album), COALESCE(t.track_no, 0), lower(t.title), t.track_id "
           "LIMIT ?")
    with db() as conn:
        rows = [dict(r) for r in conn.execute(sql, (*args, limit + 1)).fetchall()]
    more = len(rows) > limit
    rows = rows[:limit]
    return {"items": rows, "next_cursor": _enc(rows[-1]) if more and rows else None}


def stats() -> dict:
    with db() as conn:
        one = conn.execute("SELECT COUNT(*), COALESCE(SUM(duration_s), 0), COUNT(DISTINCT lower(artist)) "
                           "FROM module_radiostream_tracks WHERE state = 'ok'").fetchone()
        missing = conn.execute("SELECT COUNT(*) FROM module_radiostream_tracks WHERE state = 'missing'").fetchone()[0]
        errors = conn.execute("SELECT COUNT(*) FROM module_radiostream_scan_errors").fetchone()[0]
        formats = dict(conn.execute("SELECT format, COUNT(*) FROM module_radiostream_tracks WHERE state = 'ok' "
                                    "GROUP BY format ORDER BY COUNT(*) DESC").fetchall())
        decades = conn.execute("SELECT (year / 10) * 10 AS d, COUNT(*) FROM module_radiostream_tracks "
                               "WHERE state = 'ok' AND year IS NOT NULL GROUP BY d ORDER BY d").fetchall()
    return {"tracks": one[0], "duration_s": round(one[1], 1), "artists": one[2], "missing": missing,
            "errors": errors, "formats": formats, "genres": genres(limit=10)["items"],
            "decades": [{"decade": d, "count": n} for d, n in decades]}


def artists(limit: int = 500) -> dict:
    with db() as conn:
        rows = conn.execute("SELECT artist, COUNT(*) FROM module_radiostream_tracks WHERE state = 'ok' AND "
                            "artist != '' GROUP BY lower(artist) ORDER BY lower(artist) LIMIT ?", (limit,)).fetchall()
    return {"items": [{"artist": a, "count": n} for a, n in rows]}


def genres(limit: int = 500) -> dict:
    with db() as conn:
        rows = conn.execute("SELECT genre, COUNT(*) AS n FROM module_radiostream_tracks WHERE state = 'ok' AND "
                            "genre != '' GROUP BY lower(genre) ORDER BY n DESC, lower(genre) LIMIT ?",
                            (limit,)).fetchall()
    return {"items": [{"genre": g, "count": n} for g, n in rows]}
