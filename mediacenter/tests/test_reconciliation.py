from __future__ import annotations

from datetime import UTC, datetime

from backend import job_store, reconciliation


def _uncertain(until="2026-07-27T10:00:00Z"):
    job, _ = job_store.claim_new(
        result_id="result-1", owner="alice", media_type="movie", title="Film",
        category="movies", now="2026-07-26T10:00:00Z",
        action_expires_at="2026-07-26T10:15:00Z",
    )
    job_store.transition(
        "alice", job.result_id, job.claim_token, expected="claimed_prewrite",
        target="submitting", now="2026-07-26T10:00:01Z",
    )
    return job_store.transition(
        "alice", job.result_id, job.claim_token, expected="submitting",
        target="uncertain", now="2026-07-26T10:00:02Z", uncertain_until=until,
    )


async def test_reconciliation_marks_found_handoff_consumed(monkeypatch):
    job = _uncertain()
    monkeypatch.setattr(reconciliation, "resolve_sab_connection", lambda _: object())

    async def found(connection, markers):
        assert markers == {job.handoff_id}
        return {job.handoff_id: "SABnzbd_nzo_found"}

    monkeypatch.setattr(reconciliation, "find_handoffs", found)
    result = await reconciliation.reconcile_job(
        "alice", job, now=datetime(2026, 7, 26, 11, tzinfo=UTC)
    )
    assert result.state == "consumed"
    assert result.sab_job_id == "SABnzbd_nzo_found"


async def test_reconciliation_requires_manual_review_after_24h(monkeypatch):
    job = _uncertain(until="2026-07-26T11:00:00Z")
    monkeypatch.setattr(reconciliation, "resolve_sab_connection", lambda _: object())

    async def missing(*_):
        return {}

    monkeypatch.setattr(reconciliation, "find_handoffs", missing)
    result = await reconciliation.reconcile_job(
        "alice", job, now=datetime(2026, 7, 26, 12, tzinfo=UTC)
    )
    assert result.state == "manual_review_required"


async def test_stale_prewrite_claim_returns_available_without_sab(monkeypatch):
    job, _ = job_store.claim_new(
        result_id="result-1", owner="alice", media_type="movie", title="Film",
        category="movies", now="2026-07-26T10:00:00Z",
        action_expires_at="2026-07-26T10:15:00Z",
    )
    result = await reconciliation.reconcile_job(
        "alice", job, now=datetime(2026, 7, 26, 10, 16, tzinfo=UTC)
    )
    assert result.state == "available"
