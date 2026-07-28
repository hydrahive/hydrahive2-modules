from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from hydrahive.db.connection import db
from hydrahive.settings import settings


def _stamp(value: datetime) -> str:
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def _fingerprint(turn_id: str, turn: str, salt: str = "") -> str:
    key = settings.secret_key.encode()
    # Ohne Salt bleibt die Nutzlast byte-identisch zum Einzel-Download-Pfad,
    # damit sich dessen Grant-Bindung nicht aendert. Mit Salt (der result_id)
    # erhaelt jeder Treffer eines Sammel-Downloads einen eigenen Fingerprint —
    # sonst kollidiert der UNIQUE(owner,session_id,operation,turn_fingerprint)
    # und nur der erste Treffer bekaeme einen gueltigen Grant.
    parts = (turn_id, turn) if not salt else (turn_id, turn, salt)
    payload = "\0".join(parts).encode()
    return hmac.new(key, payload, hashlib.sha256).hexdigest()


def issue(
    *, owner: str, session_id: str, result_id: str, media_type: str,
    trusted_turn: str, trusted_turn_id: str, now: datetime | None = None,
    fingerprint_salt: str = "",
) -> str:
    moment = now or datetime.now(UTC)
    grant_id = secrets.token_urlsafe(24)
    fingerprint = _fingerprint(trusted_turn_id, trusted_turn, fingerprint_salt)
    with db(immediate=True) as conn:
        conn.execute(
            """INSERT OR IGNORE INTO module_mediacenter_action_grants
               (grant_id,owner,session_id,result_id,media_type,operation,
                turn_fingerprint,expires_at,created_at)
               VALUES (?,?,?,?,?,'enqueue',?,?,?)""",
            (grant_id, owner, session_id, result_id, media_type, fingerprint,
             _stamp(moment + timedelta(minutes=15)), _stamp(moment)),
        )
        row = conn.execute(
            """SELECT grant_id FROM module_mediacenter_action_grants
               WHERE owner=? AND session_id=?
                 AND operation='enqueue' AND turn_fingerprint=?""",
            (owner, session_id, fingerprint),
        ).fetchone()
    return row["grant_id"]


def consume_in_transaction(
    conn, *, grant_id: str, owner: str, session_id: str,
    result_id: str, media_type: str, now: str,
) -> bool:
    changed = conn.execute(
        """UPDATE module_mediacenter_action_grants SET consumed_at=?
           WHERE grant_id=? AND owner=? AND session_id=? AND result_id=?
             AND media_type=? AND operation='enqueue' AND consumed_at IS NULL
             AND expires_at>?""",
        (now, grant_id, owner, session_id, result_id, media_type, now),
    ).rowcount
    return changed == 1
