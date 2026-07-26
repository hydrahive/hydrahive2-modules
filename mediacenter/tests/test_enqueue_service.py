from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest

from backend import enqueue_service, job_store
from backend.errors import IndexerResponseError, SabResponseError, SabUnavailable
from backend.models import ProfileDecision, RawRelease
from backend.result_store import ResultStore
from backend.sab_credentials import SabConnection

_NZB = b"<nzb><file /></nzb>"
_NOW = datetime(2026, 7, 26, 10, 0, tzinfo=UTC)


def _decision(selection_status="ready"):
    return ProfileDecision(
        release=RawRelease("Film", "guid", 100, 1, "de", None, "https://evil/nzb"),
        media_type="movie", decision="eligible", reasons=(), language="de",
        resolution="1080p", format=None, bitrate_kbps=None, score=100,
        selection_status=selection_status,
    )


def _setup(monkeypatch, *, selection_status="ready"):
    store = ResultStore(ttl_seconds=60)
    result_id = store.put("alice", _decision(selection_status))
    monkeypatch.setattr(enqueue_service, "RESULTS", store)
    monkeypatch.setattr(enqueue_service, "resolve_indexer_api_key", lambda _: "idx-key")
    monkeypatch.setattr(
        enqueue_service, "resolve_sab_connection",
        lambda _: SabConnection("https://sabnzb.home.server.ha", "sab-key"),
    )
    return store, result_id


async def test_enqueue_is_idempotent_and_consumes_result(monkeypatch):
    store, result_id = _setup(monkeypatch)
    calls = []

    async def fetch(key, guid):
        assert (key, guid) == ("idx-key", "guid")
        return _NZB

    async def upload(*args, **kwargs):
        calls.append(kwargs)
        return "SABnzbd_nzo_abc"

    monkeypatch.setattr(enqueue_service.newznab, "fetch_nzb", fetch)
    monkeypatch.setattr(enqueue_service, "upload_nzb", upload)
    first = await enqueue_service.enqueue_result("alice", result_id, now=_NOW)
    second = await enqueue_service.enqueue_result("alice", result_id, now=_NOW)

    assert first.state == second.state == "consumed"
    assert first.sab_job_id == "SABnzbd_nzo_abc"
    assert len(calls) == 1
    assert calls[0]["handoff_id"].startswith("hh-")
    assert store.get("alice", result_id) is None


async def test_direct_ui_selection_satisfies_open_quality_choice(monkeypatch):
    _, result_id = _setup(monkeypatch, selection_status="quality_preference_required")
    monkeypatch.setattr(
        enqueue_service.newznab, "fetch_nzb", lambda *_: _async_value(_NZB)
    )
    monkeypatch.setattr(
        enqueue_service, "upload_nzb", lambda *_args, **_kwargs: _async_value("SABnzbd_nzo_ui")
    )

    job = await enqueue_service.enqueue_result("alice", result_id, now=_NOW)

    assert job.state == "consumed"
    assert job.sab_job_id == "SABnzbd_nzo_ui"


async def test_agent_cannot_bypass_open_quality_choice(monkeypatch):
    _, result_id = _setup(monkeypatch, selection_status="quality_preference_required")

    with pytest.raises(IndexerResponseError) as exc_info:
        await enqueue_service.enqueue_result(
            "alice", result_id, now=_NOW, require_grant=True,
            grant_id="grant", session_id="session",
        )

    assert exc_info.value.code == "result_unavailable"


async def test_prewrite_failure_releases_for_retry(monkeypatch):
    store, result_id = _setup(monkeypatch)

    async def fail(*_):
        raise RuntimeError("indexer down")

    monkeypatch.setattr(enqueue_service.newznab, "fetch_nzb", fail)
    with pytest.raises(RuntimeError):
        await enqueue_service.enqueue_result("alice", result_id, now=_NOW)

    assert job_store.get("alice", result_id).state == "available"
    assert store.get("alice", result_id).claim_id is None


@pytest.mark.parametrize(
    "error,expected",
    [(SabUnavailable("down"), "uncertain"),
     (SabResponseError("sab_upload_rejected"), "available")],
)
async def test_postwrite_error_uses_safe_state(monkeypatch, error, expected):
    store, result_id = _setup(monkeypatch)
    monkeypatch.setattr(
        enqueue_service.newznab, "fetch_nzb", lambda *_: _async_value(_NZB)
    )

    async def fail_upload(*args, **kwargs):
        raise error

    monkeypatch.setattr(enqueue_service, "upload_nzb", fail_upload)
    with pytest.raises(type(error)):
        await enqueue_service.enqueue_result("alice", result_id, now=_NOW)

    job = job_store.get("alice", result_id)
    assert job.state == expected
    if expected == "uncertain":
        assert store.get("alice", result_id).claim_id is not None
        async def reconciliation_down(username, current, *, now=None):
            raise SabUnavailable("sab_unavailable")

        monkeypatch.setattr(enqueue_service, "reconcile_job", reconciliation_down)
        again = await enqueue_service.enqueue_result("alice", result_id, now=_NOW)
        assert again.state == "uncertain"
    else:
        assert store.get("alice", result_id).claim_id is None


async def test_parallel_enqueue_does_not_reconcile_active_submit(monkeypatch):
    _, result_id = _setup(monkeypatch)
    started = asyncio.Event()
    finish = asyncio.Event()
    monkeypatch.setattr(
        enqueue_service.newznab, "fetch_nzb", lambda *_: _async_value(_NZB)
    )

    async def delayed_upload(*args, **kwargs):
        started.set()
        await finish.wait()
        return "SABnzbd_nzo_parallel"

    monkeypatch.setattr(enqueue_service, "upload_nzb", delayed_upload)
    first = asyncio.create_task(enqueue_service.enqueue_result("alice", result_id, now=_NOW))
    await started.wait()

    duplicate = await enqueue_service.enqueue_result("alice", result_id, now=_NOW)

    assert duplicate.state == "submitting"
    assert job_store.get("alice", result_id).state == "submitting"
    finish.set()
    completed = await first
    assert completed.state == "consumed"


async def test_cancellation_after_submit_becomes_uncertain(monkeypatch):
    _, result_id = _setup(monkeypatch)
    monkeypatch.setattr(
        enqueue_service.newznab, "fetch_nzb", lambda *_: _async_value(_NZB)
    )

    async def wait_forever(*args, **kwargs):
        await asyncio.Event().wait()

    monkeypatch.setattr(enqueue_service, "upload_nzb", wait_forever)
    task = asyncio.create_task(
        enqueue_service.enqueue_result("alice", result_id, now=_NOW)
    )
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert job_store.get("alice", result_id).state == "uncertain"


async def _async_value(value):
    return value
