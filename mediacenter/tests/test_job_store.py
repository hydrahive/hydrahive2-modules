from __future__ import annotations

import pytest

from backend import job_store


_ARGS = dict(
    result_id="result-1", owner="alice", media_type="movie", title="Film",
    category="film", now="2026-07-26T10:00:00Z",
    action_expires_at="2026-07-26T10:15:00Z",
)


def test_claim_is_persistent_and_idempotent():
    first, created = job_store.claim_new(**_ARGS)
    second, created_again = job_store.claim_new(**_ARGS)

    assert created is True
    assert created_again is False
    assert second == first
    assert first.state == "claimed_prewrite"
    assert first.attempt_count == 1
    assert first.claim_token
    assert first.handoff_id.startswith("hh-")


def test_claim_does_not_reveal_foreign_result():
    job_store.claim_new(**_ARGS)
    with pytest.raises(LookupError, match="result_unavailable"):
        job_store.claim_new(**{**_ARGS, "owner": "bob"})
    assert job_store.get("bob", "result-1") is None


def test_transitions_are_compare_and_swap_and_require_claim_token():
    job, _ = job_store.claim_new(**_ARGS)
    submitting = job_store.transition(
        "alice", "result-1", job.claim_token, expected="claimed_prewrite",
        target="submitting", now="2026-07-26T10:00:01Z",
    )
    assert submitting is not None
    assert submitting.state == "submitting"
    assert submitting.submitting_at == "2026-07-26T10:00:01Z"
    assert job_store.transition(
        "alice", "result-1", job.claim_token, expected="claimed_prewrite",
        target="available", now="2026-07-26T10:00:02Z",
    ) is None
    assert job_store.transition(
        "alice", "result-1", "wrong", expected="submitting",
        target="consumed", now="2026-07-26T10:00:03Z", sab_job_id="SABnzbd_nzo_x",
    ) is None


def test_consumed_requires_sab_id_and_clears_claim():
    job, _ = job_store.claim_new(**_ARGS)
    job_store.transition(
        "alice", "result-1", job.claim_token, expected="claimed_prewrite",
        target="submitting", now="2026-07-26T10:00:01Z",
    )
    consumed = job_store.transition(
        "alice", "result-1", job.claim_token, expected="submitting",
        target="consumed", now="2026-07-26T10:00:02Z", sab_job_id="SABnzbd_nzo_abc",
    )
    assert consumed is not None
    assert consumed.state == "consumed"
    assert consumed.sab_job_id == "SABnzbd_nzo_abc"
    assert consumed.claim_token is None
