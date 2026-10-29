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


# --- Hängen gebliebenes Einlesen (Befund Hauptserver 29.10.2026) -------------------------------------------------------
# Am 27.10. brach ein Einlesen durch Server-Neustarts nach 126.074 Titeln ab. In der DB blieb state='scanning' ohne
# last_scan_finished stehen; der Speicher-Zustand war nach dem Neustart leer. Folge: Die Seite zeigte nichts Klares,
# und das nächtliche Einlesen startete nie, weil es nur nach einem FERTIGEN ersten Durchgang anspringt.

def _set(**cols):
    from hydrahive.db.connection import db
    with db() as conn:
        conn.execute(f"UPDATE module_radiostream_sources SET {', '.join(f'{k} = ?' for k in cols)}", tuple(cols.values()))
        conn.commit()


def test_haengendes_scanning_wird_beim_start_aufgeraeumt(db_ready, safe):
    settings_store.save(owner="boss", url="smb://nas.test/Musik", credential_name=safe)
    _set(state="scanning", last_scan_started="2026-10-27T12:10:10Z", last_scan_finished=None)
    assert nightly.recover_interrupted() is True
    src = settings_store.get()
    assert src["state"] == "error" and src["last_scan_error"] == "radiostream_scan_interrupted"
    assert src["last_scan_started"] == "2026-10-27T12:10:10Z" and src["last_scan_finished"] is None


def test_laufendes_einlesen_wird_nicht_angefasst(db_ready, safe):
    settings_store.save(owner="boss", url="smb://nas.test/Musik", credential_name=safe)
    _set(state="scanning", last_scan_started="2026-10-29T20:00:00Z")
    assert scan_state.try_begin()
    try:
        assert nightly.recover_interrupted() is False
        assert settings_store.get()["state"] == "scanning"
    finally:
        scan_state.finish()


@pytest.mark.parametrize("state", ["idle", "error"])
def test_ohne_haengendes_scanning_nichts(db_ready, safe, state):
    settings_store.save(owner="boss", url="smb://nas.test/Musik", credential_name=safe)
    _set(state=state, last_scan_error=None)
    assert nightly.recover_interrupted() is False
    assert settings_store.get()["state"] == state and settings_store.get()["last_scan_error"] is None


def test_ohne_quelle_kein_aufraeumen(db_ready):
    assert nightly.recover_interrupted() is False


def test_abgebrochenes_erstes_einlesen_wird_nachts_nachgeholt(db_ready, safe, started):
    """Erstes Einlesen wurde per Knopf gestartet, aber nie fertig → nachts um 4 trotzdem weitermachen."""
    settings_store.save(owner="boss", url="smb://nas.test/Musik", credential_name=safe)
    _set(state="error", last_scan_error="radiostream_scan_interrupted", last_scan_started="2026-10-27T12:10:10Z",
         last_scan_finished=None)
    assert nightly.due(_local(3)) is False
    assert nightly.due(_local(4)) is True


def test_nie_gestartet_bleibt_beim_knopf(db_ready, safe, started):
    """Wurde noch nie eingelesen (kein last_scan_started), startet nachts weiterhin nichts – erstes Mal per Knopf."""
    settings_store.save(owner="boss", url="smb://nas.test/Musik", credential_name=safe)
    assert settings_store.get()["last_scan_started"] is None
    assert nightly.due(_local(4)) is False


async def test_tick_raeumt_zuerst_auf_und_holt_dann_nach(db_ready, safe, started, monkeypatch):
    """Der erste Job-Lauf nach dem Neustart räumt auf; ist es 4 Uhr, startet er gleich den Nachholer."""
    settings_store.save(owner="boss", url="smb://nas.test/Musik", credential_name=safe)
    _set(state="scanning", last_scan_started="2026-10-27T12:10:10Z", last_scan_finished=None)
    monkeypatch.setattr(nightly, "_now", lambda: _local(4))
    await nightly.tick()
    assert settings_store.get()["last_scan_error"] == "radiostream_scan_interrupted"
    assert started == [1]
