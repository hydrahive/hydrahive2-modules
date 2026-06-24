"""Highscore-Store — Scores pro User, plus globale Bestenliste.

Jede beendete Partie schreibt eine Zeile. Abfragen:
  - best_for: höchster Score eines Users in einem Spiel
  - recent_for: letzte Partien eines Users (user-scoped)
  - leaderboard: bester Score JE User je Spiel, absteigend (über alle User)
"""
from __future__ import annotations

from hydrahive.db.connection import db

_NOW = "strftime('%Y-%m-%dT%H:%M:%SZ','now')"


def add(user: str, game_id: str, score: int) -> bool:
    """Score speichern. True, wenn es ein neuer persönlicher Rekord ist."""
    with db() as c:
        prev = c.execute(
            'SELECT MAX(score) FROM module_minigames_scores '
            'WHERE "user" = ? AND game_id = ?',
            (user, game_id),
        ).fetchone()[0]
        c.execute(
            'INSERT INTO module_minigames_scores ("user", game_id, score, created_at) '
            f"VALUES (?, ?, ?, {_NOW})",
            (user, game_id, score),
        )
        return prev is None or score > int(prev)


def best_for(user: str, game_id: str) -> int:
    with db() as c:
        row = c.execute(
            'SELECT MAX(score) FROM module_minigames_scores '
            'WHERE "user" = ? AND game_id = ?',
            (user, game_id),
        ).fetchone()
        return int(row[0]) if row and row[0] is not None else 0


def recent_for(user: str, game_id: str, limit: int = 5) -> list[dict]:
    with db() as c:
        return [
            dict(r) for r in c.execute(
                'SELECT score, created_at FROM module_minigames_scores '
                'WHERE "user" = ? AND game_id = ? '
                "ORDER BY id DESC LIMIT ?",
                (user, game_id, limit),
            ).fetchall()
        ]


def leaderboard(game_id: str, limit: int = 10) -> list[dict]:
    """Top-N: bester Score je User in diesem Spiel, absteigend."""
    with db() as c:
        rows = c.execute(
            'SELECT "user" AS user, MAX(score) AS score, MAX(created_at) AS created_at '
            "FROM module_minigames_scores WHERE game_id = ? "
            'GROUP BY "user" ORDER BY score DESC, created_at ASC LIMIT ?',
            (game_id, limit),
        ).fetchall()
        return [
            {"rank": i + 1, "user": r["user"], "score": int(r["score"]), "created_at": r["created_at"]}
            for i, r in enumerate(rows)
        ]
