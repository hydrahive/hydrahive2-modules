"""Ergebnis-Store — Partie-Ergebnisse pro User + globale Bestenliste.

Jede beendete Partie schreibt eine Zeile (win/loss/draw aus User-Sicht).
Abfragen:
  - record_for: W/L/D-Bilanz eines Users in einem Spiel (optional Modus)
  - leaderboard: meiste Siege je User je Spiel, absteigend (über alle User)
"""
from __future__ import annotations

from hydrahive.db.connection import db

_NOW = "strftime('%Y-%m-%dT%H:%M:%SZ','now')"


def add(user: str, game_id: str, mode: str, result: str, opponent: str) -> None:
    with db() as c:
        c.execute(
            'INSERT INTO module_boardgames_results '
            '("user", game_id, mode, result, opponent, created_at) '
            f"VALUES (?, ?, ?, ?, ?, {_NOW})",
            (user, game_id, mode, result, opponent),
        )


def record_for(user: str, game_id: str, mode: str | None = None) -> dict:
    clause = 'WHERE "user" = ? AND game_id = ?'
    params: list = [user, game_id]
    if mode:
        clause += " AND mode = ?"
        params.append(mode)
    with db() as c:
        rows = c.execute(
            f"SELECT result, COUNT(*) AS n FROM module_boardgames_results {clause} "
            "GROUP BY result",
            params,
        ).fetchall()
    rec = {"win": 0, "loss": 0, "draw": 0}
    for r in rows:
        if r["result"] in rec:
            rec[r["result"]] = int(r["n"])
    rec["total"] = rec["win"] + rec["loss"] + rec["draw"]
    return rec


def leaderboard(game_id: str, limit: int = 10) -> list[dict]:
    """Top-N: meiste Siege je User in diesem Spiel, absteigend."""
    with db() as c:
        rows = c.execute(
            'SELECT "user" AS user, '
            "SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) AS wins, "
            "COUNT(*) AS games "
            "FROM module_boardgames_results WHERE game_id = ? "
            'GROUP BY "user" HAVING wins > 0 '
            "ORDER BY wins DESC, games ASC LIMIT ?",
            (game_id, limit),
        ).fetchall()
        return [
            {"rank": i + 1, "user": r["user"], "wins": int(r["wins"]), "games": int(r["games"])}
            for i, r in enumerate(rows)
        ]
