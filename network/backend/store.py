"""Speicher des Moduls: Minuten-Messung, Ereignisse (ohne Dubletten), Speedtests, Verlauf der Dream Machine."""
from __future__ import annotations

from hydrahive.db.connection import db

SAMPLE_COLS = ("ts", "lan_loss", "lan_rtt", "fritz_loss", "fritz_rtt", "inet_loss", "inet_rtt_min", "inet_rtt_avg",
               "inet_rtt_max", "inet_jitter", "fritz_link", "fritz_conn", "fritz_access", "path")
EVENT_COLS = ("event_id", "source", "ts", "kind", "wan", "duration_s", "detail")
SPEED_COLS = ("source", "ts", "down_mbit", "up_mbit", "ping_ms", "server")
SERIES_COLS = ("scale", "ts", "latency_avg", "latency_min", "latency_max", "rx_bytes", "tx_bytes")


def _ins(conn, table: str, cols: tuple, rows: list[dict], verb: str) -> int:
    sql = f"{verb} INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})"
    before = conn.total_changes
    conn.executemany(sql, [tuple(r.get(c) for c in cols) for r in rows])
    return conn.total_changes - before


def add_sample(s: dict) -> None:
    with db() as conn:
        _ins(conn, "module_network_samples", SAMPLE_COLS, [{"path": "unknown", **s}], "INSERT OR REPLACE")


def samples(start: int, end: int) -> list[dict]:
    with db() as conn:
        rows = conn.execute(f"SELECT {', '.join(SAMPLE_COLS)} FROM module_network_samples WHERE ts >= ? AND ts <= ? "
                            "ORDER BY ts", (start, end)).fetchall()
    return [dict(r) for r in rows]


def latest_sample() -> dict | None:
    with db() as conn:
        r = conn.execute(f"SELECT {', '.join(SAMPLE_COLS)} FROM module_network_samples ORDER BY ts DESC LIMIT 1"
                         ).fetchone()
    return dict(r) if r else None


def add_events(rows: list[dict]) -> int:
    with db() as conn:
        return _ins(conn, "module_network_events", EVENT_COLS, rows, "INSERT OR IGNORE")


def events(start: int, end: int) -> list[dict]:
    with db() as conn:
        rows = conn.execute(f"SELECT {', '.join(EVENT_COLS)} FROM module_network_events WHERE ts >= ? AND ts <= ? "
                            "ORDER BY ts, event_id", (start, end)).fetchall()
    return [dict(r) for r in rows]


def last_event_ts(source: str) -> int | None:
    with db() as conn:
        r = conn.execute("SELECT MAX(ts) FROM module_network_events WHERE source = ?", (source,)).fetchone()
    return r[0] if r else None


def add_speedtests(rows: list[dict]) -> int:
    with db() as conn:
        return _ins(conn, "module_network_speedtests", SPEED_COLS, rows, "INSERT OR IGNORE")


def speedtests(start: int, end: int) -> list[dict]:
    with db() as conn:
        rows = conn.execute(f"SELECT {', '.join(SPEED_COLS)} FROM module_network_speedtests WHERE ts >= ? AND ts <= ? "
                            "ORDER BY ts", (start, end)).fetchall()
    return [dict(r) for r in rows]


def put_series(rows: list[dict]) -> int:
    with db() as conn:
        return _ins(conn, "module_network_udm_series", SERIES_COLS, rows, "INSERT OR REPLACE")


def series(scale: str, start: int, end: int) -> list[dict]:
    with db() as conn:
        rows = conn.execute(f"SELECT {', '.join(SERIES_COLS)} FROM module_network_udm_series WHERE scale = ? "
                            "AND ts >= ? AND ts <= ? ORDER BY ts", (scale, start, end)).fetchall()
    return [dict(r) for r in rows]
