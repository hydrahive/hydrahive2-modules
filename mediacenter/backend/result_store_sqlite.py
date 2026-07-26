from __future__ import annotations

import math
import secrets
import time
from dataclasses import replace

from hydrahive.db.connection import db

from .config import RESULT_TTL_SECONDS
from .models import ProfileDecision
from .result_codec import deserialize_profile_decision, serialize_profile_decision
from .result_store import ResultStoreFull, StoredResult


class SQLiteResultStore:
    """Prozessübergreifender TTL-/Claim-Store in der HydraHive-SQLite-DB."""

    def __init__(self, *, ttl_seconds: int = RESULT_TTL_SECONDS, max_entries: int = 250,
                 claim_ttl_seconds: int | None = None) -> None:
        if ttl_seconds <= 0 or max_entries <= 0 or (
            claim_ttl_seconds is not None and claim_ttl_seconds <= 0
        ):
            raise ValueError("result_store_configuration_invalid")
        self._ttl = ttl_seconds
        self._claim_ttl = claim_ttl_seconds or ttl_seconds
        self._max_entries = max_entries

    @staticmethod
    def _time(now: float | None) -> float:
        value = time.time() if now is None else now
        if not math.isfinite(value):
            raise ValueError("result_store_timestamp_invalid")
        return value

    @staticmethod
    def _cleanup(conn, now: float) -> None:
        conn.execute(
            """DELETE FROM module_mediacenter_results
               WHERE (claim_id IS NULL AND expires_at<=?) OR
                     (claim_id IS NOT NULL AND claim_expires_at<=? AND expires_at<=?)""",
            (now, now, now),
        )
        conn.execute(
            """UPDATE module_mediacenter_results
               SET claim_id=NULL,claim_expires_at=NULL
               WHERE claim_id IS NOT NULL AND claim_expires_at<=? AND expires_at>?""",
            (now, now),
        )

    @staticmethod
    def _decode(row) -> StoredResult | None:
        try:
            decision = deserialize_profile_decision(row["payload_json"])
        except ValueError:
            return None
        return StoredResult(
            row["owner"], decision, row["expires_at"], row["claim_id"],
            row["claim_expires_at"], row["selection_session_id"],
        )

    def _owned(self, conn, owner: str, result_id: str, now: float) -> StoredResult | None:
        self._cleanup(conn, now)
        row = conn.execute(
            """SELECT owner,payload_json,expires_at,claim_id,claim_expires_at,
                      selection_session_id FROM module_mediacenter_results
               WHERE result_id=? AND owner=?""",
            (result_id, owner),
        ).fetchone()
        if row is None:
            return None
        item = self._decode(row)
        if item is None:
            conn.execute(
                "DELETE FROM module_mediacenter_results WHERE result_id=? AND owner=?",
                (result_id, owner),
            )
        return item

    def put(self, owner: str, decision: ProfileDecision, *, now: float | None = None) -> str:
        if not isinstance(owner, str) or not 1 <= len(owner) <= 256:
            raise ValueError("result_store_owner_invalid")
        timestamp = self._time(now)
        payload = serialize_profile_decision(decision)
        if len(payload) > 131_072:
            raise ValueError("result_store_payload_too_large")
        with db(immediate=True) as conn:
            self._cleanup(conn, timestamp)
            count = conn.execute(
                "SELECT COUNT(*) FROM module_mediacenter_results WHERE owner=?", (owner,)
            ).fetchone()[0]
            while count >= self._max_entries:
                candidate = conn.execute(
                    """SELECT result_id FROM module_mediacenter_results
                       WHERE owner=? AND claim_id IS NULL
                       ORDER BY expires_at,created_at LIMIT 1""", (owner,),
                ).fetchone()
                if candidate is None:
                    raise ResultStoreFull("result_store_owner_capacity")
                conn.execute(
                    "DELETE FROM module_mediacenter_results WHERE result_id=?",
                    (candidate["result_id"],),
                )
                count -= 1
            while True:
                result_id = secrets.token_urlsafe(24)
                if conn.execute(
                    """INSERT OR IGNORE INTO module_mediacenter_results
                       (result_id,owner,payload_json,expires_at,created_at)
                       VALUES (?,?,?,?,?)""",
                    (result_id, owner, payload, timestamp + self._ttl, timestamp),
                ).rowcount == 1:
                    return result_id

    def get(self, owner: str, result_id: str, *, now: float | None = None) -> StoredResult | None:
        with db(immediate=True) as conn:
            return self._owned(conn, owner, result_id, self._time(now))

    def claim(self, owner: str, result_id: str, *, now: float | None = None) -> StoredResult | None:
        timestamp = self._time(now)
        with db(immediate=True) as conn:
            item = self._owned(conn, owner, result_id, timestamp)
            if item is None or item.claim_id is not None:
                return None
            claim_id = secrets.token_urlsafe(24)
            expiry = timestamp + self._claim_ttl
            changed = conn.execute(
                """UPDATE module_mediacenter_results SET claim_id=?,claim_expires_at=?
                   WHERE result_id=? AND owner=? AND claim_id IS NULL""",
                (claim_id, expiry, result_id, owner),
            ).rowcount
            return replace(item, claim_id=claim_id, claim_expires_at=expiry) if changed else None

    def renew(self, owner: str, result_id: str, claim_id: str,
              *, now: float | None = None) -> bool:
        timestamp = self._time(now)
        with db(immediate=True) as conn:
            item = self._owned(conn, owner, result_id, timestamp)
            if item is None or item.claim_id is None or not secrets.compare_digest(item.claim_id, claim_id):
                return False
            return conn.execute(
                """UPDATE module_mediacenter_results SET claim_expires_at=?
                   WHERE result_id=? AND owner=? AND claim_id=?""",
                (timestamp + self._claim_ttl, result_id, owner, claim_id),
            ).rowcount == 1

    def release(self, owner: str, result_id: str, claim_id: str,
                *, now: float | None = None) -> bool:
        timestamp = self._time(now)
        with db(immediate=True) as conn:
            item = self._owned(conn, owner, result_id, timestamp)
            if item is None or item.claim_id is None or not secrets.compare_digest(item.claim_id, claim_id):
                return False
            if item.expires_at <= timestamp:
                query = "DELETE FROM module_mediacenter_results WHERE result_id=? AND owner=? AND claim_id=?"
            else:
                query = "UPDATE module_mediacenter_results SET claim_id=NULL,claim_expires_at=NULL WHERE result_id=? AND owner=? AND claim_id=?"
            return conn.execute(query, (result_id, owner, claim_id)).rowcount == 1

    def consume(self, owner: str, result_id: str, claim_id: str,
                *, now: float | None = None) -> ProfileDecision | None:
        with db(immediate=True) as conn:
            item = self._owned(conn, owner, result_id, self._time(now))
            if item is None or item.claim_id is None or not secrets.compare_digest(item.claim_id, claim_id):
                return None
            deleted = conn.execute(
                "DELETE FROM module_mediacenter_results WHERE result_id=? AND owner=? AND claim_id=?",
                (result_id, owner, claim_id),
            ).rowcount
            return item.decision if deleted else None

    def mark_selection_challenge(self, owner, result_id, session_id, *, now=None):
        from .result_store_sql_selection import mark_challenge
        return mark_challenge(self, owner, result_id, session_id, now)

    def unlock_selection(self, owner, result_id, preference, *, session_id=None, now=None):
        from .result_store_sql_selection import unlock
        return unlock(self, owner, result_id, preference, session_id, now)

    def clear(self) -> None:
        with db(immediate=True) as conn:
            conn.execute("DELETE FROM module_mediacenter_results")
