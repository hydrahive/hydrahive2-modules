"""Versandgrenze je Konto (PLAN-M2 Schritt 4, Spec §11). Gleitendes Fenster von einer Stunde, Standard 20 Mails.

Einstellbar über HH_MAILBOX_SEND_PER_HOUR (1–1000). Gezählt wird nur Zeitpunkt und Anzahl Empfänger – kein Inhalt.
Einträge älter als ein Tag werden beim Schreiben aufgeräumt.
"""
from __future__ import annotations

import math
import os
import time

from hydrahive.db.connection import db

DEFAULT = 20
WINDOW = 3600.0
KEEP = 86400.0


class RateLimited(RuntimeError):
    def __init__(self, retry_after: int):
        super().__init__(f"Versandgrenze erreicht – wieder möglich in {retry_after} s")
        self.retry_after = retry_after


def limit() -> int:
    try:
        v = int(os.environ.get("HH_MAILBOX_SEND_PER_HOUR", "") or DEFAULT)
    except ValueError:
        return DEFAULT
    return v if 1 <= v <= 1000 else DEFAULT


def check(account_id: str) -> None:
    now = time.time()
    n = limit()
    with db() as c:
        rows = c.execute("SELECT sent_at FROM module_mailbox_sendlog WHERE account_id=? AND sent_at>? "
                         "ORDER BY sent_at DESC LIMIT ?", (account_id, now - WINDOW, n)).fetchall()
    if len(rows) >= n:
        oldest = rows[-1][0]
        raise RateLimited(max(1, math.ceil(oldest + WINDOW - now)))


def record(account_id: str, *, recipients: int) -> None:
    now = time.time()
    with db() as c:
        c.execute("DELETE FROM module_mailbox_sendlog WHERE sent_at<?", (now - KEEP,))
        c.execute("INSERT INTO module_mailbox_sendlog(account_id, sent_at, recipients) VALUES (?,?,?)",
                  (account_id, now, int(recipients)))
