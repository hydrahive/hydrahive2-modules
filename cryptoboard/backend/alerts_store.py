"""Alert-Store — Preis-/Portfolio-Alert-Regeln + Event-Historie, user-scoped.

Regeln in module_cryptoboard_alerts, ausgelöste Benachrichtigungen in
module_cryptoboard_alert_events. Alle Ops filtern strikt auf "user". Geldwerte
in EUR.
"""
from __future__ import annotations

from hydrahive.db.connection import db

_NOW = "strftime('%Y-%m-%dT%H:%M:%SZ','now')"
_MAX = 200

KINDS = (
    "price_above", "price_below",
    "pct_change_24h_above", "pct_change_24h_below",
    "portfolio_above", "portfolio_below",
)
_PORTFOLIO_KINDS = ("portfolio_above", "portfolio_below")

_COLS = "id, kind, coin_id, symbol, threshold, active, last_value, last_fired, note, created_at"


def is_portfolio(kind: str) -> bool:
    return kind in _PORTFOLIO_KINDS


# ------------------------------------------------------------------ Regeln
def list_for(user: str) -> list[dict]:
    with db() as c:
        return [
            dict(r) for r in c.execute(
                f'SELECT {_COLS} FROM module_cryptoboard_alerts WHERE "user" = ? '
                "ORDER BY created_at DESC",
                (user,),
            ).fetchall()
        ]


def list_active_all() -> list[dict]:
    """Alle aktiven Alerts aller User — für den Poller."""
    with db() as c:
        return [
            dict(r) for r in c.execute(
                f'SELECT "user", {_COLS} FROM module_cryptoboard_alerts WHERE active = 1'
            ).fetchall()
        ]


def add(user: str, *, kind: str, coin_id: str, symbol: str, threshold: float, note: str) -> int:
    if kind not in KINDS:
        raise ValueError("invalid_kind")
    with db() as c:
        count = c.execute(
            'SELECT COUNT(*) FROM module_cryptoboard_alerts WHERE "user" = ?', (user,)
        ).fetchone()[0]
        if count >= _MAX:
            raise ValueError("alerts_full")
        cur = c.execute(
            'INSERT INTO module_cryptoboard_alerts '
            '("user", kind, coin_id, symbol, threshold, note, created_at) '
            f"VALUES (?, ?, ?, ?, ?, ?, {_NOW})",
            (user, kind, coin_id, symbol, threshold, note),
        )
        return int(cur.lastrowid)


def set_active(user: str, alert_id: int, active: bool) -> bool:
    with db() as c:
        cur = c.execute(
            'UPDATE module_cryptoboard_alerts SET active = ? WHERE "user" = ? AND id = ?',
            (1 if active else 0, user, alert_id),
        )
        return cur.rowcount > 0


def remove(user: str, alert_id: int) -> bool:
    with db() as c:
        cur = c.execute(
            'DELETE FROM module_cryptoboard_alerts WHERE "user" = ? AND id = ?',
            (user, alert_id),
        )
        return cur.rowcount > 0


def update_state(alert_id: int, *, last_value: float, fired: bool) -> None:
    """Poller-Callback: letzten Wert merken, optional last_fired setzen."""
    with db() as c:
        if fired:
            c.execute(
                f"UPDATE module_cryptoboard_alerts SET last_value = ?, last_fired = {_NOW} "
                "WHERE id = ?",
                (last_value, alert_id),
            )
        else:
            c.execute(
                "UPDATE module_cryptoboard_alerts SET last_value = ? WHERE id = ?",
                (last_value, alert_id),
            )


# ------------------------------------------------------------------ Events
def add_event(
    user: str, *, alert_id: int, kind: str, coin_id: str, symbol: str,
    threshold: float, value: float, message: str,
) -> None:
    with db() as c:
        c.execute(
            'INSERT INTO module_cryptoboard_alert_events '
            '("user", alert_id, kind, coin_id, symbol, threshold, value, message, created_at) '
            f"VALUES (?, ?, ?, ?, ?, ?, ?, ?, {_NOW})",
            (user, alert_id, kind, coin_id, symbol, threshold, value, message),
        )


def list_events(user: str, limit: int = 50) -> list[dict]:
    limit = max(1, min(200, limit))
    with db() as c:
        return [
            dict(r) for r in c.execute(
                'SELECT id, alert_id, kind, coin_id, symbol, threshold, value, message, seen, created_at '
                'FROM module_cryptoboard_alert_events WHERE "user" = ? '
                "ORDER BY created_at DESC LIMIT ?",
                (user, limit),
            ).fetchall()
        ]


def unseen_count(user: str) -> int:
    with db() as c:
        return c.execute(
            'SELECT COUNT(*) FROM module_cryptoboard_alert_events WHERE "user" = ? AND seen = 0',
            (user,),
        ).fetchone()[0]


def mark_seen(user: str) -> None:
    with db() as c:
        c.execute(
            'UPDATE module_cryptoboard_alert_events SET seen = 1 WHERE "user" = ? AND seen = 0',
            (user,),
        )
