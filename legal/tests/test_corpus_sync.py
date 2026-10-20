"""Abgleich der Kernliste: Fehler je Gesetz brechen nicht alles ab, Protokoll in module_legal_sync (Plan L1 Schritt 5)."""
from __future__ import annotations

import asyncio
import json

import pytest
from backend import corpus_list, corpus_store, corpus_sync, gii_fetch
from conftest import fixture_xml


def test_core_list_matches_spec_54_unique_keys():
    keys = corpus_list.core_keys()
    assert len(keys) == 54 and len(set(keys)) == 54
    assert {"bgb", "famfg", "woeigg", "bbaug", "stgb", "sgb_10", "owig_1968"} <= set(keys)


@pytest.fixture
def fake_fetch(monkeypatch):
    fails = {}

    async def fetch(key):
        if key in fails:
            raise gii_fetch.FetchError(fails[key])
        return fixture_xml(key)

    monkeypatch.setattr(gii_fetch, "fetch_law_xml", fetch)
    monkeypatch.setattr(corpus_sync, "PAUSE_SECONDS", 0)
    return fails


def _last_run():
    from hydrahive.db.connection import db
    with db() as c:
        row = c.execute("SELECT state, laws_total, laws_changed, errors, finished_at FROM module_legal_sync "
                        "ORDER BY id DESC LIMIT 1").fetchone()
    return {"state": row[0], "total": row[1], "changed": row[2], "errors": json.loads(row[3]), "finished": row[4]}


def test_sync_loads_laws_and_logs_run(fake_fetch):
    res = asyncio.run(corpus_sync.run(["bgb", "owig_1968"]))
    assert res["changed"] == 2 and res["errors"] == []
    run = _last_run()
    assert run["state"] == "done" and run["total"] == 2 and run["changed"] == 2 and run["finished"]
    assert corpus_store.get_norm("BGB", "§ 536c") and corpus_store.get_norm("OWiG", "§ 67")
    assert corpus_store.get_law("bgb")["pinned"] is True


def test_second_run_without_change_changes_nothing(fake_fetch):
    asyncio.run(corpus_sync.run(["bgb"]))
    assert asyncio.run(corpus_sync.run(["bgb"]))["changed"] == 0


def test_one_failing_law_does_not_stop_the_others(fake_fetch):
    fake_fetch["vwgo"] = "HTTP 500"
    res = asyncio.run(corpus_sync.run(["bgb", "vwgo", "owig_1968"]))
    assert res["changed"] == 2
    assert res["errors"] == [{"key": "vwgo", "error": "HTTP 500"}]
    assert _last_run()["state"] == "done"
    assert corpus_store.get_norm("OWiG", "§ 67")


def test_broken_xml_counts_as_error(fake_fetch, monkeypatch):
    async def broken(key):
        return b"<dokumente></dokumente>"
    monkeypatch.setattr(gii_fetch, "fetch_law_xml", broken)
    res = asyncio.run(corpus_sync.run(["bgb"]))
    assert res["changed"] == 0 and res["errors"][0]["key"] == "bgb"


def test_due_logic_daily_after_20h(fake_fetch):
    assert corpus_sync.is_due(None, now="2026-10-20T10:00:00Z") is True
    assert corpus_sync.is_due("2026-10-20T03:30:00Z", now="2026-10-20T20:00:00Z") is False
    assert corpus_sync.is_due("2026-10-20T03:30:00Z", now="2026-10-20T23:31:00Z") is True


def test_concurrent_run_is_refused(fake_fetch, monkeypatch):
    from backend import corpus_sync as cs
    monkeypatch.setattr(cs, "_RUNNING", True)
    with pytest.raises(cs.SyncBusy):
        asyncio.run(cs.run(["bgb"]))
