"""Regressionstests für abgebrochene Deep-Research-Läufe."""
from __future__ import annotations

import asyncio
from unittest.mock import Mock

import pytest

import backend
from backend import recovery, service

RESTART_ERROR = "Durch Neustart abgebrochen – bitte neu starten"


@pytest.mark.asyncio
async def test_recovery_marks_orphaned_queued_and_running_runs():
    queued = service.create_run("alice", "Wartende Recherche", None)
    running = service.create_run("alice", "Laufende Recherche", None)
    done = service.create_run("alice", "Fertige Recherche", None)
    service._update(running["id"], status="running")
    service._update(done["id"], status="done")

    changed = await recovery.recover_stale_runs()

    assert changed == 2
    queued_after = service.get_run("alice", queued["id"])
    running_after = service.get_run("alice", running["id"])
    assert (queued_after["status"], queued_after["error"]) == ("error", RESTART_ERROR)
    assert (running_after["status"], running_after["error"]) == ("error", RESTART_ERROR)
    assert service.get_run("alice", done["id"])["status"] == "done"


@pytest.mark.asyncio
async def test_recovery_preserves_live_run_during_module_reload(monkeypatch):
    started = asyncio.Event()
    release = asyncio.Event()

    async def waiting_research(*args, **kwargs):
        started.set()
        await release.wait()
        return {"category": "general", "stats": {}, "markdown": "", "sources": []}

    monkeypatch.setattr(service, "run_research", waiting_research)
    run = service.create_run("alice", "Noch laufende Recherche", None)
    task = asyncio.create_task(
        service._execute_run(run["id"], run["question"], None, None, None),
        name="legacy-task-before-module-reload",
    )
    await started.wait()
    task.set_name("legacy-task-before-module-reload")

    try:
        assert await recovery.recover_stale_runs() == 0
        assert service.get_run("alice", run["id"])["status"] == "running"
    finally:
        release.set()
        await task


@pytest.mark.asyncio
async def test_execution_stores_readable_error_and_logs_details(monkeypatch, caplog):
    raw_error = "litellm.BadRequestError: LLM Provider NOT provided, model=go"

    async def failing_research(*args, **kwargs):
        raise RuntimeError(raw_error)

    monkeypatch.setattr(service, "run_research", failing_research)
    run = service.create_run("alice", "Fehlerhafte Recherche", None)

    await service._execute_run(run["id"], run["question"], None, None, None)

    stored = service.get_run("alice", run["id"])["error"]
    assert stored == "Das ausgewählte KI-Modell ist nicht korrekt konfiguriert."
    assert raw_error in caplog.text


def test_registers_immediate_recovery_job():
    ctx = Mock()

    backend.register(ctx)

    ctx.register_job.assert_called_once_with(
        "recover_stale_runs",
        recovery.recover_stale_runs,
        interval_seconds=300,
        initial_delay_seconds=0,
    )
