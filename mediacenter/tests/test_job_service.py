from __future__ import annotations

from backend import job_service, job_store


def _consumed(owner: str, result_id: str, sab_id: str):
    job, _ = job_store.claim_new(
        result_id=result_id, owner=owner, media_type="movie", title=f"Film {owner}",
        category="movies", now="2026-07-26T10:00:00Z",
        action_expires_at="2026-07-26T10:15:00Z",
    )
    job_store.transition(
        owner, result_id, job.claim_token, expected="claimed_prewrite",
        target="submitting", now="2026-07-26T10:00:01Z",
    )
    return job_store.transition(
        owner, result_id, job.claim_token, expected="submitting",
        target="consumed", now="2026-07-26T10:00:02Z", sab_job_id=sab_id,
    )


async def test_history_only_projects_callers_tracked_jobs(monkeypatch):
    alice = _consumed("alice", "result-alice", "SABnzbd_nzo_alice")
    _consumed("bob", "result-bob", "SABnzbd_nzo_bob")
    monkeypatch.setattr(job_service, "resolve_sab_connection", lambda _: object())

    async def statuses(connection, mode, allowed_ids):
        assert mode == "history"
        assert allowed_ids == {"SABnzbd_nzo_alice"}
        return {
            "SABnzbd_nzo_alice": {
                "status": "completed", "progress": 100.0,
                "eta": None, "error_code": None,
            },
            "SABnzbd_nzo_bob": {
                "status": "failed", "progress": None,
                "eta": None, "error_code": "sab_job_failed",
            },
        }

    monkeypatch.setattr(job_service, "fetch_owned_status", statuses)
    rows = await job_service.list_jobs("alice", "history")
    assert len(rows) == 1
    assert rows[0]["result_id"] == alice.result_id
    assert "bob" not in str(rows)


def test_list_owned_is_hard_limited_and_owner_scoped():
    for index in range(3):
        job_store.claim_new(
            result_id=f"alice-{index}", owner="alice", media_type="movie",
            title="Film", category="movies", now=f"2026-07-26T10:00:0{index}Z",
            action_expires_at="2026-07-26T10:15:00Z",
        )
    job_store.claim_new(
        result_id="bob-1", owner="bob", media_type="movie", title="Other",
        category="movies", now="2026-07-26T10:00:04Z",
        action_expires_at="2026-07-26T10:15:00Z",
    )
    rows = job_store.list_owned("alice", limit=2)
    assert len(rows) == 2
    assert all(row.owner == "alice" for row in rows)
