"""Sender-Einstellungen (eine Zeile, module_radiostream_station). Alles über die Oberfläche (Till 29.10.)."""
from __future__ import annotations

from hydrahive.db.connection import db

DEFAULTS = {"name": "Radiostream", "subtitle": "", "artist_gap_min": 60, "title_gap_days": 3, "listen_port": 8800,
            "reach": "all", "max_listeners": 50}
LIMITS = {"artist_gap_min": (0, 24 * 60), "title_gap_days": (0, 60), "listen_port": (1024, 65535),
          "max_listeners": (1, 1000)}
REACH = ("all", "home", "off")
RESERVED_PORTS = {8001, 8810, 3001}         # HydraHive, Icecast intern, Gitea


class StationError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def get() -> dict:
    with db() as conn:
        row = conn.execute("SELECT name, subtitle, artist_gap_min, title_gap_days, listen_port, reach, max_listeners "
                           "FROM module_radiostream_station WHERE id = 1").fetchone()
    return dict(row) if row else dict(DEFAULTS)


def save(*, user: str, **changes) -> dict:
    cur = get()
    for k, v in changes.items():
        if k not in DEFAULTS:
            raise StationError("radiostream_station_invalid")
        if k in LIMITS:
            lo, hi = LIMITS[k]
            if not isinstance(v, int) or isinstance(v, bool) or not lo <= v <= hi:
                raise StationError("radiostream_port_invalid" if k == "listen_port" else "radiostream_station_invalid")
        if k == "listen_port" and v in RESERVED_PORTS:
            raise StationError("radiostream_port_invalid")
        if k == "reach" and v not in REACH:
            raise StationError("radiostream_station_invalid")
        if k in ("name", "subtitle"):
            v = " ".join(str(v).split())[:80]
            if k == "name" and not v:
                raise StationError("radiostream_station_invalid")
        cur[k] = v
    with db() as conn:
        conn.execute(
            "INSERT INTO module_radiostream_station (id, name, subtitle, artist_gap_min, title_gap_days, listen_port, "
            "reach, max_listeners, updated_by, updated_at) VALUES (1, :name, :subtitle, :artist_gap_min, "
            ":title_gap_days, :listen_port, :reach, :max_listeners, :user, strftime('%Y-%m-%dT%H:%M:%SZ','now')) "
            "ON CONFLICT(id) DO UPDATE SET name = excluded.name, subtitle = excluded.subtitle, "
            "artist_gap_min = excluded.artist_gap_min, title_gap_days = excluded.title_gap_days, "
            "listen_port = excluded.listen_port, reach = excluded.reach, max_listeners = excluded.max_listeners, "
            "updated_by = excluded.updated_by, updated_at = excluded.updated_at",
            {**cur, "user": user})
        conn.commit()
    return get()
