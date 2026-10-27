"""Automatisches Einlesen (SPEC: „register_job prüft stündlich, ob ein Durchgang fällig ist – Standard täglich 4 Uhr;
beim ersten Mal startet der Durchgang über den Knopf“)."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from backend import nightly, scan_state, settings_store


@pytest.fixture
def started(monkeypatch):
    calls = []
    monkeypatch.setattr(nightly.scanner, "start_in_background", lambda: calls.append(1))
    return calls


def _at(h, day=27):
    return datetime(2026, 10, day, h, 5, tzinfo=timezone.utc).astimezone()


def _local(h, day=27):
    return datetime(2026, 10, day, h, 5).astimezone()


def test_ohne_quelle_nichts(db_ready, started):
    assert nightly.due(_local(4)) is False


def test_vor_dem_ersten_einlesen_nichts(db_ready, safe, started):
    settings_store.save(owner="boss", url="smb://nas.test/Musik", credential_name=safe)
    assert nightly.due(_local(4)) is False          # erstes Mal nur per Knopf


def test_nach_erstem_einlesen_um_vier(db_ready, safe, started):
    settings_store.save(owner="boss", url="smb://nas.test/Musik", credential_name=safe)
    settings_store.mark("idle", started=True, finished=True)
    from hydrahive.db.connection import db
    with db() as conn:
        conn.execute("UPDATE module_radiostream_sources SET last_scan_finished = '2026-10-26T03:10:00Z'")
        conn.commit()
    assert nightly.due(_local(3)) is False
    assert nightly.due(_local(4)) is True
    assert nightly.due(_local(5)) is False


def test_heute_schon_gelaufen(db_ready, safe, started):
    settings_store.save(owner="boss", url="smb://nas.test/Musik", credential_name=safe)
    now = _local(4)
    from hydrahive.db.connection import db
    with db() as conn:
        conn.execute("UPDATE module_radiostream_sources SET last_scan_finished = ?",
                     (now.replace(minute=1).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),))
        conn.commit()
    assert nightly.due(now) is False


def test_laeuft_gerade(db_ready, safe, started):
    settings_store.save(owner="boss", url="smb://nas.test/Musik", credential_name=safe)
    from hydrahive.db.connection import db
    with db() as conn:
        conn.execute("UPDATE module_radiostream_sources SET last_scan_finished = '2026-10-20T03:00:00Z'")
        conn.commit()
    assert scan_state.try_begin()
    try:
        assert nightly.due(_local(4)) is False
    finally:
        scan_state.finish()


async def test_tick_startet_wenn_faellig(db_ready, monkeypatch, started):
    monkeypatch.setattr(nightly, "due", lambda now=None: True)
    await nightly.tick()
    assert started == [1]
    monkeypatch.setattr(nightly, "due", lambda now=None: False)
    await nightly.tick()
    assert started == [1]
