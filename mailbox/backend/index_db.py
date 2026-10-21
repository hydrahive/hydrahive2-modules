"""Eigener Index <archiv>/index.sqlite (PLAN-M1 „zwei Datenbanken“): Ordner, Nachrichten, Volltext.

Er kann groß werden (alle Jahre) und liegt deshalb nicht in sessions.db. Aus den .eml jederzeit neu aufbaubar.
Ohne FTS5 (manches Python auf dem Mac) entsteht der Index ohne Volltext-Tabelle; die Suche nutzt dann LIKE.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from . import paths

_SCHEMA = """
CREATE TABLE IF NOT EXISTS folders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id TEXT NOT NULL,
  name TEXT NOT NULL,                   -- IMAP-Name (UTF-7 dekodiert)
  role TEXT NOT NULL DEFAULT '',        -- inbox | sent | drafts | trash | junk | archive | ''
  uidvalidity INTEGER NOT NULL DEFAULT 0,
  last_uid INTEGER NOT NULL DEFAULT 0,
  total INTEGER NOT NULL DEFAULT 0,
  unread INTEGER NOT NULL DEFAULT 0,
  gone INTEGER NOT NULL DEFAULT 0,      -- Ordner gibt es auf dem Server nicht mehr (Inhalt bleibt im Archiv)
  UNIQUE(account_id, name)
);
CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id TEXT NOT NULL,
  folder_id INTEGER NOT NULL REFERENCES folders(id),
  uid INTEGER,                          -- NULL, wenn auf dem Server weg
  message_id TEXT NOT NULL DEFAULT '',
  sha256 TEXT NOT NULL,
  thread_key TEXT NOT NULL DEFAULT '',
  in_reply_to TEXT NOT NULL DEFAULT '',
  date TEXT NOT NULL DEFAULT '',        -- ISO, UTC
  from_addr TEXT NOT NULL DEFAULT '',
  to_addr TEXT NOT NULL DEFAULT '',
  cc_addr TEXT NOT NULL DEFAULT '',
  subject TEXT NOT NULL DEFAULT '',
  snippet TEXT NOT NULL DEFAULT '',
  seen INTEGER NOT NULL DEFAULT 0,
  flagged INTEGER NOT NULL DEFAULT 0,
  answered INTEGER NOT NULL DEFAULT 0,
  size INTEGER NOT NULL DEFAULT 0,
  attachments TEXT NOT NULL DEFAULT '[]',
  path TEXT NOT NULL,                   -- relativ zu archive_root
  deleted_on_server INTEGER NOT NULL DEFAULT 0,
  parse_error TEXT NOT NULL DEFAULT '',
  UNIQUE(account_id, sha256)
);
CREATE INDEX IF NOT EXISTS messages_folder_date ON messages(folder_id, date DESC);
CREATE INDEX IF NOT EXISTS messages_account_date ON messages(account_id, date DESC);
CREATE INDEX IF NOT EXISTS messages_thread ON messages(account_id, thread_key);
CREATE INDEX IF NOT EXISTS messages_msgid ON messages(account_id, message_id);
CREATE INDEX IF NOT EXISTS messages_uid ON messages(folder_id, uid);
"""
_FTS_ARGS = "subject, from_addr, to_addr, body, content='', contentless_delete=1, tokenize='unicode61 remove_diacritics 2'"
_FTS = f"CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5({_FTS_ARGS});"
_ready: set[str] = set()


def _fts5_available(conn: sqlite3.Connection) -> bool:
    try:
        # genau die Definition des Index prüfen (contentless_delete gibt es erst ab SQLite 3.43)
        conn.execute(f"CREATE VIRTUAL TABLE IF NOT EXISTS temp._fts5_probe USING fts5({_FTS_ARGS})")
        conn.execute("DROP TABLE temp._fts5_probe")
        return True
    except sqlite3.OperationalError:
        return False


def _setup(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(_SCHEMA)
    if _fts5_available(conn):
        conn.executescript(_FTS)


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    root = paths.archive_root()
    root.mkdir(parents=True, exist_ok=True)
    path = root / "index.sqlite"
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        if str(path) not in _ready or not path.exists():
            _setup(conn)
            _ready.add(str(path))
        conn.execute("PRAGMA foreign_keys=ON")
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def has_fts() -> bool:
    with connect() as c:
        return c.execute("SELECT 1 FROM sqlite_master WHERE name='messages_fts'").fetchone() is not None
