"""Expliziter Live-Smoke-Test: Suche → Enqueue → Queue/History.

Start nur mit bewusst gewähltem, legal herunterladbarem Treffer:
MEDIACENTER_LIVE_E2E=I_UNDERSTAND_THIS_ENQUEUES \
MEDIACENTER_E2E_USER=till MEDIACENTER_E2E_QUERY='…' \
MEDIACENTER_E2E_TITLE='exakter bereinigter Release-Titel' \
MEDIACENTER_E2E_SIZE_BYTES=123456 python -m scripts.live_e2e
"""
from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

from backend import enqueue_service, job_service, reconciliation, service
from backend.credentials import resolve_indexer_api_key
from backend.models import SearchRequest
from backend.sab_credentials import resolve_sab_connection
from hydrahive.db import init_db
from hydrahive.modules.migrations import apply_module_migrations
from hydrahive.settings import settings

MODULE_DIR = Path(__file__).resolve().parents[1]


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"missing:{name}")
    return value


async def main() -> None:
    if os.environ.get("MEDIACENTER_LIVE_E2E") != "I_UNDERSTAND_THIS_ENQUEUES":
        raise SystemExit("live_e2e_not_explicitly_enabled")
    username = _required("MEDIACENTER_E2E_USER")
    query = _required("MEDIACENTER_E2E_QUERY")
    title = _required("MEDIACENTER_E2E_TITLE")
    try:
        size_bytes = int(_required("MEDIACENTER_E2E_SIZE_BYTES"))
    except ValueError:
        raise SystemExit("invalid:MEDIACENTER_E2E_SIZE_BYTES") from None
    if size_bytes < 1:
        raise SystemExit("invalid:MEDIACENTER_E2E_SIZE_BYTES")
    media_type = os.environ.get("MEDIACENTER_E2E_MEDIA_TYPE", "movie")
    timeout = min(max(int(os.environ.get("MEDIACENTER_E2E_TIMEOUT", "600")), 30), 1800)

    indexer_key = resolve_indexer_api_key(username)
    sab_connection = resolve_sab_connection(username)
    with tempfile.TemporaryDirectory(prefix="mediacenter-live-e2e-") as root:
        settings.sessions_db = Path(root) / "sessions.sqlite"
        init_db()
        apply_module_migrations("mediacenter", MODULE_DIR / "migrations")
        service.resolve_indexer_api_key = lambda _username: indexer_key
        enqueue_service.resolve_indexer_api_key = lambda _username: indexer_key
        enqueue_service.resolve_sab_connection = lambda _username: sab_connection
        job_service.resolve_sab_connection = lambda _username: sab_connection
        reconciliation.resolve_sab_connection = lambda _username: sab_connection

        connections = await service.test_connections(username)
        print("connections", connections.ok, bool(connections.sab_version), flush=True)
        response = await service.search_indexer(
            username,
            SearchRequest(query=query, media_type=media_type, limit=100),
            owner_id=username,
        )
        matches = [
            item for item in response.results
            if item.decision == "eligible"
            and item.title == title
            and item.size_bytes == size_bytes
            and item.result_id
        ]
        if len(matches) != 1:
            raise SystemExit("exact_unique_eligible_release_not_found")
        selected = matches[0]
        print("selected", selected.title, selected.resolution or selected.format, flush=True)
        job = await enqueue_service.enqueue_result(
            username, selected.result_id, owner_id=username, priority="low"
        )
        print("enqueue", job.state, bool(job.sab_job_id), flush=True)

        saw_queue = False
        for _ in range(timeout // 5):
            queue = await job_service.list_jobs(username, "queue", owner_id=username)
            saw_queue = saw_queue or any(
                item["result_id"] == selected.result_id for item in queue
            )
            history = await job_service.list_jobs(username, "history", owner_id=username)
            finished = next(
                (item for item in history if item["result_id"] == selected.result_id), None
            )
            if finished:
                print("history", finished["status"], finished["error_code"], flush=True)
                print("live_e2e_ok", saw_queue, flush=True)
                return
            await asyncio.sleep(5)
        raise SystemExit("live_e2e_history_timeout")


if __name__ == "__main__":
    asyncio.run(main())
