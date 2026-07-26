from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass

from hydrahive.db.connection import db


@dataclass(frozen=True)
class JobRecord:
    result_id: str
    owner: str
    media_type: str
    title: str
    category: str
    state: str
    claim_token: str | None
    handoff_id: str
    attempt_count: int
    sab_job_id: str | None
    error_code: str | None
    action_expires_at: str
    state_changed_at: str
    submitting_at: str | None
    uncertain_until: str | None


def _record(row) -> JobRecord:
    return JobRecord(**{name: row[name] for name in JobRecord.__dataclass_fields__})


def handoff_id(result_id: str) -> str:
    digest = hashlib.sha256(result_id.encode()).hexdigest()[:24]
    return f"hh-{digest}"


def _audit(conn, row, action: str, now: str) -> None:
    result_hash = hashlib.sha256(row["result_id"].encode()).hexdigest()
    conn.execute(
        """INSERT INTO module_mediacenter_audit
           (owner,agent_id,session_id,action,media_type,result_hash,title,
            sab_job_id,state,error_code,created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (row["owner"], row["agent_id"], row["session_id"], action,
         row["media_type"], result_hash, row["title"], row["sab_job_id"],
         row["state"], row["error_code"], now),
    )


def get(owner: str, result_id: str) -> JobRecord | None:
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM module_mediacenter_jobs WHERE result_id=? AND owner=?",
            (result_id, owner),
        ).fetchone()
    return _record(row) if row else None


def claim_new(
    *, result_id: str, owner: str, media_type: str, title: str,
    category: str, now: str, action_expires_at: str,
    agent_id: str | None = None, session_id: str | None = None,
    profile_summary: str = "{}",
) -> tuple[JobRecord, bool]:
    token = secrets.token_urlsafe(24)
    marker = handoff_id(result_id)
    with db(immediate=True) as conn:
        row = conn.execute(
            "SELECT * FROM module_mediacenter_jobs WHERE result_id=?", (result_id,)
        ).fetchone()
        if row:
            if row["owner"] != owner:
                raise LookupError("result_unavailable")
            return _record(row), False
        conn.execute(
            """INSERT INTO module_mediacenter_jobs
               (result_id,owner,media_type,title,category,state,claim_token,handoff_id,
                attempt_count,action_expires_at,state_changed_at,created_at,updated_at,
                agent_id,session_id,profile_summary)
               VALUES (?,?,?,?,?,'claimed_prewrite',?,?,1,?,?,?,?,?,?,?)""",
            (result_id, owner, media_type, title, category, token, marker,
             action_expires_at, now, now, now, agent_id, session_id, profile_summary),
        )
        row = conn.execute(
            "SELECT * FROM module_mediacenter_jobs WHERE result_id=?", (result_id,)
        ).fetchone()
        _audit(conn, row, "claim", now)
    return _record(row), True


def reclaim_available(owner: str, result_id: str, *, now: str) -> JobRecord | None:
    token = secrets.token_urlsafe(24)
    with db(immediate=True) as conn:
        changed = conn.execute(
            """UPDATE module_mediacenter_jobs
               SET state='claimed_prewrite', claim_token=?, attempt_count=attempt_count+1,
                   state_changed_at=?, updated_at=?, error_code=NULL
               WHERE result_id=? AND owner=? AND state='available'""",
            (token, now, now, result_id, owner),
        ).rowcount
        if changed != 1:
            return None
        row = conn.execute(
            "SELECT * FROM module_mediacenter_jobs WHERE result_id=?", (result_id,)
        ).fetchone()
        _audit(conn, row, "reclaim", now)
    return _record(row)


def transition(
    owner: str, result_id: str, claim_token: str, *, expected: str,
    target: str, now: str, sab_job_id: str | None = None,
    error_code: str | None = None, uncertain_until: str | None = None,
) -> JobRecord | None:
    submitting_at = now if target in {"submitting", "uncertain"} else None
    with db(immediate=True) as conn:
        changed = conn.execute(
            """UPDATE module_mediacenter_jobs
               SET state=?, state_changed_at=?, updated_at=?, sab_job_id=COALESCE(?,sab_job_id),
                   error_code=?, uncertain_until=COALESCE(?,uncertain_until),
                   submitting_at=COALESCE(submitting_at,?),
                   claim_token=CASE WHEN ? IN ('available','consumed') THEN NULL ELSE claim_token END
               WHERE result_id=? AND owner=? AND claim_token=? AND state=?""",
            (target, now, now, sab_job_id, error_code, uncertain_until,
             submitting_at, target, result_id, owner, claim_token, expected),
        ).rowcount
        if changed != 1:
            return None
        row = conn.execute(
            "SELECT * FROM module_mediacenter_jobs WHERE result_id=?", (result_id,)
        ).fetchone()
        _audit(conn, row, f"transition:{expected}:{target}", now)
    return _record(row)


def list_owned(owner: str, *, limit: int = 100) -> list[JobRecord]:
    safe_limit = max(1, min(limit, 100))
    with db() as conn:
        rows = conn.execute(
            """SELECT * FROM module_mediacenter_jobs WHERE owner=?
               ORDER BY updated_at DESC LIMIT ?""",
            (owner, safe_limit),
        ).fetchall()
    return [_record(row) for row in rows]


def clear_all() -> None:
    with db() as conn:
        conn.execute("DELETE FROM module_mediacenter_audit")
        conn.execute("DELETE FROM module_mediacenter_jobs")
